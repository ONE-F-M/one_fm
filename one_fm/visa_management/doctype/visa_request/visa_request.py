# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VisaRequest(Document):
	def validate(self):
		self.validate_workflow_transitions()
		self.validate_references()

	def validate_workflow_transitions(self):
		# PAM -> MOI: require pam_reference_number when workflow becomes Pending By MOI
		if (self.workflow_state in ("Pending By MOI", "Pending By MOI")) and (not self.get("pam_reference_number")):
			frappe.throw(
				"PAM Reference Number is required before submitting to MOI.",
				title="Missing PAM Reference Number",
			)

		# MOI -> Pending Visa: require moi_reference_number
		if (self.workflow_state in ("Pending Visa", "Pending visa")) and (not self.get("moi_reference_number")):
			frappe.throw(
				"MOI Reference Number is required before moving to Pending Visa.",
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