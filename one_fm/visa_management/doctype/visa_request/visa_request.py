# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists

# WI-001976: the state a PAM rejection lands in, and the two reasons that are worth
# reapplying under. Both are reasons the application itself can be corrected for - a
# designation that needs specifying, or a gender that does not match the profession -
# unlike a black-listed worker or an active file, where a new request would be refused
# for the same cause.
#
# The strings are the ones the Reject dialog offers (WI-001693) and writes into
# pam_rejection_remark; the work item names them "Designation" and "Gender".
PAM_REJECTED_STATE = "Rejected By PAM"
REAPPLY_REASONS = (
	"The occupation requires amendment to specify the worker's specialization",
	"The worker's gender does not match the profession",
)

# Cleared on the new request. Everything else is copied - the AC asks for the Job Offer
# and Job Applicant, and the applicant's own details have to come with them or the new
# draft cannot even be saved (the passport copy is mandatory and has nothing to fetch
# from). What must not carry over is the outcome of the attempt that failed.
OUTCOME_FIELDS = (
	"operator_rejection_remark",
	"grd_manager_remark",
	"pam_rejection_remark",
	"moi_rejection_remark",
	"pam_reference_number",
	"pam_remarks",
	"pam_decision_date",
	"custom_work_permit_number",
	"moi_reference_number",
	"moi_remarks",
	"moi_decision_date",
	"visa_reference_number",
	"visa_issue_date",
	"visa_expiry_date",
	"visa_document",
	"payment_receipt",
	"payment_date",
)
from frappe.utils import add_months, add_years, getdate, nowdate

# WI-001975: the eligibility a Draft has to clear before it can be saved. Both are
# government requirements rather than internal policy, so they are checked at the door -
# an applicant who fails them cannot be put through the visa process at all.
MINIMUM_PASSPORT_VALIDITY_MONTHS = 18
MINIMUM_APPLICANT_AGE_YEARS = 21


class VisaRequest(Document):
	def validate(self):
		self.validate_applicant_eligibility()
		self.validate_workflow_transitions()
		self.validate_references()
		self.update_tracker_status()

	def validate_applicant_eligibility(self):
		"""Hold a Draft to the passport and age rules (WI-001975).

		Only in Draft. A record that has already moved into the workflow was accepted on
		the day it was raised, and re-checking it here would strand it: the passport
		carries on ageing while the application is in progress, so a visa halfway through
		PAM would become unsaveable through no fault of the operator.
		"""
		if (self.workflow_state or "Draft") != "Draft":
			return

		self.validate_passport_validity()
		self.validate_applicant_age()

	def validate_passport_validity(self):
		if not self.passport_expires_on:
			return

		# Measured from today, not from the issue date: what matters is how much validity
		# the passport has left now. Compared by adding the months to today rather than
		# counting days, so the answer does not drift with the length of the months.
		if getdate(self.passport_expires_on) < getdate(
			add_months(nowdate(), MINIMUM_PASSPORT_VALIDITY_MONTHS)
		):
			frappe.throw(
				_(
					"The applicant's passport must be valid for at least {0} more months "
					"from today. The Visa Request cannot be saved."
				).format(MINIMUM_PASSPORT_VALIDITY_MONTHS),
				title=_("Passport Validity Too Short"),
			)

	def validate_applicant_age(self):
		if not self.date_of_birth:
			return

		if getdate(add_years(self.date_of_birth, MINIMUM_APPLICANT_AGE_YEARS)) > getdate(nowdate()):
			frappe.throw(
				_(
					"The applicant must be at least {0} years old to create a Visa Request. "
					"The Visa Request cannot be saved."
				).format(MINIMUM_APPLICANT_AGE_YEARS),
				title=_("Applicant Below Minimum Age"),
			)

	def update_tracker_status(self):
		if not self.job_offer:
			return

		ccp_name = frappe.db.get_value("Candidate Country Process", {"job_offer": self.job_offer}, "name")
		if not ccp_name:
			return

		# Keep our own candidate_country_process field in sync so this record
		# shows up correctly in the CCP's Connections panel and sibling counts.
		if self.candidate_country_process != ccp_name:
			self.candidate_country_process = ccp_name

		# Find the row in Candidate Country Process Details for Visa Processing
		rows = frappe.get_all(
			"Candidate Country Process Details",
			filters={"parent": ccp_name, "process_name": "Visa Processing"},
			fields=["name", "reference_name", "reference_type"],
			limit=1,
		)
		if rows:
			row = rows[0]
			# Visa Request's own workflow_state passes through as-is at every
			# intermediate stage; only the final "Completed" state is relabeled
			# to "Visa issued" for the candidate-facing tracker.
			display_status = "Visa issued" if self.workflow_state == "Completed" else (self.workflow_state or "Draft")
			update_fields = {
				"status": display_status,
			}
			if not row.reference_name:
				update_fields["reference_name"] = self.name
			# reference_name is a Dynamic Link keyed off reference_type -- writing
			# one without the other leaves the row unsaveable ("Reference Type must
			# be set first") the next time anything calls a full doc.save() on the
			# parent CCP, since this update bypasses Document validation.
			if not row.reference_type:
				update_fields["reference_type"] = "Visa Request"

			is_completed = (self.workflow_state == "Completed")
			# "Work Permit Cancelled" is what WI-001773 renamed the terminal cancelled
			# state to; without it a cancelled visa never stamps its actual_date on the
			# tracker and the step reads as still in progress.
			is_rejected = self.workflow_state in [
				"Rejected", "Rejected By Operator", "Rejected By PAM", "Rejected By MOI",
				"Rejected for Re Issue", "Work Permit Cancelled", "Cancelled"
			]
			if is_completed or is_rejected:
				update_fields["actual_date"] = frappe.utils.nowdate()
			else:
				update_fields["actual_date"] = None

			frappe.db.set_value(
				"Candidate Country Process Details",
				row.name,
				update_fields,
				update_modified=True
			)

	def on_update(self):
		# WI-001977: a Visa Copy or Payment Receipt just attached is read by OCR.
		queue_document_ocr(self)

		if self.job_offer:
			ccp_name = frappe.db.get_value("Candidate Country Process", {"job_offer": self.job_offer}, "name")
			if ccp_name:
				from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import recalculate_ccp_live_eta
				recalculate_ccp_live_eta(ccp_name)

	def validate_workflow_transitions(self):
		# PAM -> MOI: require pam_reference_number when workflow becomes Pending By MOI
		if self.workflow_state == "Pending By MOI" and not self.get("pam_reference_number"):
			frappe.throw(
				"PAM Reference Number is required before submitting to MOI.",
				title="Missing PAM Reference Number",
			)

		# MOI -> Pending Visa Issuance: require moi_reference_number
		if self.workflow_state == "Pending Visa Issuance" and not self.get("moi_reference_number"):
			frappe.throw(
				"MOI Reference Number is required before moving to Pending Visa Issuance.",
				title="Missing MOI Reference Number",
			)

	def validate_references(self):
		# Pending Visa -> Pending Recruiter Confirmation: require visa_reference_number, payment_receipt, visa_document
		if (self.workflow_state == "Pending Recruiter Confirmation"):
			missing = []
			if not self.get("visa_reference_number"):
				missing.append("Visa Reference Number")
			if not self.get("payment_receipt"):
				missing.append("Payment Receipt")
			if not self.get("visa_document"):
				missing.append("Visa Document")

			if missing:
				frappe.throw(
					"The following fields are required before submitting to recruiter: {0}".format(
						", ".join(missing)
					),
					title="Missing Required Fields",
				)

def can_reapply(doc) -> bool:
	"""Is this request one the GRD Operator may raise a fresh attempt for (WI-001976)?

	The gate the button and the server share, so the button cannot offer something the
	method then refuses.
	"""
	return (
		doc.get("workflow_state") == PAM_REJECTED_STATE
		and doc.get("pam_rejection_remark") in REAPPLY_REASONS
	)


@frappe.whitelist(methods=["POST"])
def reapply_visa_request(name: str):
	"""Raise a fresh Visa Request from one PAM rejected (WI-001976).

	Named ``<original>-1`` - the amendment series the AC asks for - but not through
	Frappe's amendment machinery: ``amended_from`` may only point at a cancelled
	document, and a Rejected By PAM request is still a draft (the workflow gives that
	state docstatus 0), so it can neither be submitted nor cancelled to qualify. The
	number is allocated by Frappe's own append_number_if_name_exists, so a second
	reapplication becomes -2 rather than colliding.

	The rejected request is left exactly as it is. It is the history the AC asks to keep,
	and ``reapplied_from`` on the new one is the link back to it.
	"""
	source = frappe.get_doc("Visa Request", name)
	source.check_permission("read")

	if not frappe.has_permission("Visa Request", "create"):
		frappe.throw(
			_("You do not have permission to create a Visa Request."), frappe.PermissionError
		)

	if not can_reapply(source):
		frappe.throw(
			_(
				"{0} can only be reapplied from <b>{1}</b>, and only when PAM rejected it for "
				"the designation or the worker's gender."
			).format(source.name, PAM_REJECTED_STATE),
			title=_("Cannot Reapply"),
		)

	reapplication = frappe.copy_doc(source)
	for fieldname in OUTCOME_FIELDS:
		reapplication.set(fieldname, None)

	reapplication.workflow_state = "Draft"
	reapplication.reapplied_from = source.name

	# Taken from the original's base name, so reapplying VR-08-2026-00002-1 gives -2
	# rather than -1-1. name_set is what stops autoname allocating a fresh series number
	# over the top of it.
	reapplication.name = append_number_if_name_exists("Visa Request", _base_name(source.name))
	reapplication.flags.name_set = True
	reapplication.insert()

	return {"name": reapplication.name}


# A reapplication's name is the series (which ends in the 5-digit counter) plus "-N".
_REAPPLICATION_NAME = re.compile(r"^(?P<base>.+-\d{5,})-\d{1,4}$")


def _base_name(name: str) -> str:
	"""The original series name, with any reapplication suffix removed."""
	match = _REAPPLICATION_NAME.match(name)
	return match.group("base") if match else name


# WI-001977: the attachments that are read by OCR, and the fields each one fills.
# Keyed by the Visa Request field the operator attaches to.
OCR_DOCUMENTS = {
	"visa_document": {
		"label": "Visa Copy",
		"extract": "one_fm.ocr_utils.extract_evisa_data",
		"fills": ("visa_reference_number", "visa_issue_date", "visa_expiry_date"),
	},
	"payment_receipt": {
		"label": "Payment Receipt",
		"extract": "one_fm.ocr_utils.extract_payment_receipt_data",
		"fills": ("payment_date",),
	},
}

# The state the operator attaches these in. Outside it the attachments are not the
# ones this reads - a passport copy on a Draft has nothing to do with a visa.
OCR_STATE = "Pending Visa Issuance"


def queue_document_ocr(doc, method=None):
	"""Read a freshly attached Visa Copy or Payment Receipt (WI-001977).

	Enqueued rather than run inline: Mindee is an external call that takes seconds, and
	the operator should not be made to wait on a save for it. The extracted values land
	on the form for review - nothing here advances the workflow, which is the AC's point.

	Only fires for an attachment that actually changed, so an operator's correction to an
	extracted date survives the next save.
	"""
	if doc.workflow_state != OCR_STATE:
		return

	changed = [
		fieldname
		for fieldname in OCR_DOCUMENTS
		if doc.get(fieldname) and doc.has_value_changed(fieldname)
	]
	if not changed:
		return

	frappe.enqueue(
		"one_fm.visa_management.doctype.visa_request.visa_request.run_document_ocr",
		queue="short",
		# After the commit, not before it. on_update runs inside the save transaction, and
		# a worker that picks the job up before that transaction lands re-reads the
		# document without the attachment on it - which is exactly what happened: the job
		# ran and logged "No file attached" against a request that plainly had one.
		enqueue_after_commit=True,
		visa_request=doc.name,
		fieldnames=changed,
		user=frappe.session.user,
	)


def run_document_ocr(visa_request: str, fieldnames: list, user: str | None = None):
	"""Extract from each attachment and write what came back (background job)."""
	doc = frappe.get_doc("Visa Request", visa_request)
	extracted = {}

	for fieldname in fieldnames:
		spec = OCR_DOCUMENTS[fieldname]

		if not doc.get(fieldname):
			# Removed again between the save and this job running. Nothing to read, and
			# nothing worth a traceback in the Error Log either.
			continue

		try:
			file_path = _attachment_path(doc.get(fieldname))
			extracted.update(frappe.get_attr(spec["extract"])(file_path))
		except Exception:
			# One unreadable document must not cost the other its extraction, and the
			# operator can still type the values in - so this is logged, not raised.
			frappe.log_error(
				title=f"Visa Request OCR failed — {spec['label']}",
				message=f"{visa_request}\n{frappe.get_traceback()}",
			)

	if not extracted:
		return

	doc.db_set(extracted, update_modified=False)

	frappe.publish_realtime(
		"visa_request_ocr_complete",
		{"name": visa_request, "fields": list(extracted)},
		user=user or frappe.session.user,
	)


def _attachment_path(file_url: str) -> str:
	"""Absolute path on disk for an attachment URL, public or private."""
	import os

	if not file_url:
		raise ValueError("No file attached")

	if file_url.startswith("/private/files/"):
		path = frappe.get_site_path("private", "files", file_url.split("/private/files/")[-1])
	elif file_url.startswith("/files/"):
		path = frappe.get_site_path("public", "files", file_url.split("/files/")[-1])
	else:
		path = frappe.get_site_path("public", file_url.lstrip("/"))

	if not os.path.exists(path):
		raise FileNotFoundError(f"Attachment not found on disk: {file_url}")

	return path
