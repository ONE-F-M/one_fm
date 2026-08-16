# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The attestation of an employee's Police Clearance Certificate (WI-002028).

Not to be confused with PCC Clearance, which is the recruitment-side record of obtaining
the certificate for a candidate abroad. This one tracks what happens to the certificate
once it is here: the embassy attests it, MOFA attests it, or it is translated - each step a
fee and a receipt the PRO has to produce before the file moves on.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

from one_fm.grd.utils import get_pcc_attestation_fees

ATTESTATION = "Attestation"
TRANSLATION = "Translation"

# Each receipt and the field that records when it went up. Read-only fields, stamped here
# rather than in the browser so the stamp is the server's clock and cannot be skipped by
# whatever attached the file.
RECEIPT_TIMESTAMPS = (
	("upload_embassy_payment_receipt", "upload_embassy_payment_receipt_on"),
	("upload_mofa_payment_receipt", "upload_mofa_payment_receipt_on"),
	("upload_translation_payment_receipt", "upload_translation_payment_receipt_on"),
)


class PCCAttestation(Document):
	def validate(self):
		self.set_attestation_requirements()
		self.set_receipt_timestamps()

	def on_update_after_submit(self):
		# The receipts are allow_on_submit, so a file can arrive after the record is
		# submitted. validate does not run on that path.
		self.set_receipt_timestamps()

	def set_attestation_requirements(self):
		"""Derive what this certificate needs from the candidate's nationality (WI-002025).

		The Nationality Attestation Rules in HR Settings say, per nationality, whether the
		embassy attests, whether MOFA attests, and whether the certificate has to be
		translated. All three are independent: the reporter's data has nationalities that need
		MOFA but no embassy, and one - Ugandan - that needs neither, only translation.

		Held on the record as three flags rather than inferred from the fees, because a fee of
		zero and a step that does not apply are different things, and the workflow routes on
		the difference. An embassy that attests for free still has to be visited.

		A nationality with no row in the table needs none of the three.

		Translation work never goes near an embassy or MOFA, so those two are cleared for it
		rather than left showing charges nobody will pay - and an Attestation is not a
		translation, so its translation fee is cleared for the same reason.
		"""
		fees = get_pcc_attestation_fees(self.nationality)

		if self.type == TRANSLATION:
			self.embassy_attestation_required = 0
			self.mofa_attestation_required = 0
			self.requires_embassy_attestation = 0
			self.mofa_fee = 0
			self.translation_required = 1
			self.translation_fee = fees.translation_fee
			return

		self.embassy_attestation_required = int(fees.embassy_required)
		self.mofa_attestation_required = int(fees.mofa_required)
		self.translation_required = int(fees.translation_required)

		self.requires_embassy_attestation = fees.embassy_fee
		self.mofa_fee = fees.mofa_fee
		self.translation_fee = 0

	@property
	def needs_embassy_attestation(self):
		"""Does this candidate's nationality need the embassy step at all?

		Distinct from the fee being non-zero: an embassy that attests for free still has to be
		visited, so the question is what the rule says, not what it charges.
		"""
		return self.type == ATTESTATION and bool(self.embassy_attestation_required)

	@property
	def needs_mofa_attestation(self):
		"""Does this candidate's nationality need the MOFA step at all?

		The reason this exists: the reporter's data has a nationality that needs neither
		embassy nor MOFA, and routing "not embassy" straight to Pending MOFA would have
		blocked its PRO on a receipt that was never going to exist.
		"""
		return self.type == ATTESTATION and bool(self.mofa_attestation_required)

	def set_receipt_timestamps(self):
		"""Stamp when each receipt went up, and clear the stamp if the file is removed."""
		for receipt_field, timestamp_field in RECEIPT_TIMESTAMPS:
			has_receipt = bool(self.get(receipt_field))
			has_timestamp = bool(self.get(timestamp_field))

			if has_receipt and not has_timestamp:
				self.set_field(timestamp_field, now())
			elif not has_receipt and has_timestamp:
				self.set_field(timestamp_field, None)

	def set_field(self, fieldname, value):
		"""Write a field on either side of submit.

		After submit the row is already saved, so an assignment in
		`on_update_after_submit` would be thrown away.
		"""
		if self.docstatus == 1:
			self.db_set(fieldname, value)
		else:
			self.set(fieldname, value)
