# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
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
		if not (self.passport_issued_on and self.passport_expires_on):
			return

		# Compared by adding the months to the issue date rather than counting days, so
		# the answer does not drift with the length of the months in between.
		if getdate(self.passport_expires_on) < getdate(
			add_months(self.passport_issued_on, MINIMUM_PASSPORT_VALIDITY_MONTHS)
		):
			frappe.throw(
				_(
					"The applicant's passport validity must be at least {0} months from the "
					"passport expiry date. The Visa Request cannot be saved."
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