# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002110: which PCC Attestation fields the Type shows.

An attestation and a translation are different pieces of work with different fees and
different receipts, and the form used to show every field of both at once - including,
before a Type was chosen, all of them.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

ATTESTATION = "eval:doc.type == 'Attestation'"
TRANSLATION = "eval:doc.type == 'Translation'"

# Shown only for an Attestation: the embassy and MOFA breakdown, and the receipts for them.
ATTESTATION_ONLY = (
	"embassy_attestation_required",
	"requires_embassy_attestation",
	"mofa_attestation_required",
	"mofa_fee",
	"upload_embassy_payment_receipt",
	"upload_mofa_payment_receipt",
)

# Shown only for a Translation.
TRANSLATION_ONLY = (
	"translation_required",
	"translation_fee",
	"upload_translation_payment_receipt",
)

# A stamp appears with the file it stamps, never on its own.
STAMPS = {
	"upload_embassy_payment_receipt_on": f"{ATTESTATION} && doc.upload_embassy_payment_receipt",
	"upload_mofa_payment_receipt_on": f"{ATTESTATION} && doc.upload_mofa_payment_receipt",
	"upload_translation_payment_receipt_on": f"{TRANSLATION} && doc.upload_translation_payment_receipt",
}

# Neither section means anything until a Type is chosen.
SECTIONS = ("attestation_and_cost_breakdown_section", "section_break_42")


class TestPCCAttestationFieldVisibility(FrappeTestCase):
	def setUp(self):
		self.meta = frappe.get_meta("PCC Attestation")

	def _depends_on(self, fieldname):
		field = self.meta.get_field(fieldname)
		self.assertIsNotNone(field, f"PCC Attestation has no {fieldname} field")
		return field.depends_on

	def test_the_embassy_and_mofa_fields_belong_to_an_attestation(self):
		for fieldname in ATTESTATION_ONLY:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self._depends_on(fieldname), ATTESTATION)

	def test_the_translation_fields_belong_to_a_translation(self):
		for fieldname in TRANSLATION_ONLY:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self._depends_on(fieldname), TRANSLATION)

	def test_a_receipt_stamp_waits_for_its_receipt(self):
		for fieldname, condition in STAMPS.items():
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self._depends_on(fieldname), condition)

	def test_an_unchosen_type_hides_both_sections(self):
		for fieldname in SECTIONS:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self._depends_on(fieldname), "eval:doc.type")
