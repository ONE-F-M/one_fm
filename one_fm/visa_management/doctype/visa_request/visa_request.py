# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VisaRequest(Document):
	def validate(self):
		self.validate_workflow_transitions()
		self.validate_references()
		self.update_tracker_status()

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
			fields=["name", "reference_name"],
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
