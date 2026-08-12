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

from one_fm.grd.utils import get_embassy_attestation_fee

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
		self.set_embassy_attestation_fee()
		self.set_receipt_timestamps()

	def on_update_after_submit(self):
		# The receipts are allow_on_submit, so a file can arrive after the record is
		# submitted. validate does not run on that path.
		self.set_receipt_timestamps()

	def set_embassy_attestation_fee(self):
		"""Fetch the embassy fee for the candidate's Place of Birth (WI-002025 / WI-002028).

		A country in the Embassy Cost Table means its embassy attests and charges the stated
		fee. A country absent from the table means it does not attest at all, and the fee
		stays empty - which is what `requires_embassy_attestation` is read for when the
		workflow decides whether to route through Pending Embassy.

		Translation work never goes near an embassy, so the fee is cleared for it rather
		than left showing a charge nobody will pay.
		"""
		if self.type == TRANSLATION:
			self.requires_embassy_attestation = 0
			return

		fee = get_embassy_attestation_fee(self.place_of_birth)
		self.requires_embassy_attestation = fee if fee is not None else 0

	@property
	def needs_embassy_attestation(self):
		"""Does this candidate's country attest at all?

		Distinct from the fee being non-zero: an embassy that attests for free still has to
		be visited, so the question is whether the country is in the table.
		"""
		return self.type == ATTESTATION and get_embassy_attestation_fee(self.place_of_birth) is not None

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
