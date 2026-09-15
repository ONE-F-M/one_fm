# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002109: which PACI fields show, which are required, and what unticking clears."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

DAMJ = "eval:doc.damj_is_applicable == 1"
FINE = "eval:doc.is_paci_fine_applicable == 1"
REJECTED = 'eval:doc.workflow_state == "Rejected"'

A_LETTER = "/files/damj-letter.pdf"


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPACIDamjAndFineFields(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.meta = frappe.get_meta("PACI")

	def _a_paci(self, **kwargs):
		paci = frappe.get_doc({
			"doctype": "PACI",
			"employee": self.employee,
			"category": "Renewal",
			"date_of_application": today(),
			**kwargs,
		})
		paci.flags.ignore_permissions = True
		paci.insert()
		return paci

	# ── the fields exist ──────────────────────────────────────────────────────────

	def test_the_record_can_carry_a_damj_merge(self):
		for fieldname in ("damj_is_applicable", "original_civil_id", "upload_damj_letter", "upload_damj_letter_on"):
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(self.meta.get_field(fieldname), fieldname)

	# ── visibility ────────────────────────────────────────────────────────────────

	def test_the_damj_details_follow_the_damj_checkbox(self):
		for fieldname in ("original_civil_id", "upload_damj_letter"):
			with self.subTest(fieldname=fieldname):
				field = self.meta.get_field(fieldname)
				self.assertEqual(field.depends_on, DAMJ)
				self.assertEqual(field.mandatory_depends_on, DAMJ)

	def test_the_fine_amount_follows_the_fine_checkbox(self):
		field = self.meta.get_field("paci_fine_amount_kwd")
		self.assertEqual(field.depends_on, FINE)
		self.assertEqual(field.mandatory_depends_on, FINE)
		self.assertTrue(field.non_negative)

	def test_the_whole_rejection_block_waits_for_a_rejection(self):
		"""Not only the reason - an empty section headed Rejection Details on a record nobody
		rejected is noise."""
		self.assertEqual(self.meta.get_field("rejection_details_section").depends_on, REJECTED)
		self.assertEqual(self.meta.get_field("paci_rejection_reason").depends_on, REJECTED)

	# ── required when ticked ──────────────────────────────────────────────────────

	def test_a_ticked_damj_needs_its_civil_id_and_letter(self):
		with self.assertRaises(frappe.ValidationError):
			self._a_paci(damj_is_applicable=1)

	def test_a_ticked_damj_with_both_saves(self):
		paci = self._a_paci(
			damj_is_applicable=1, original_civil_id="299010101010", upload_damj_letter=A_LETTER
		)
		self.assertEqual(paci.original_civil_id, "299010101010")

	# ── cleared when unticked ─────────────────────────────────────────────────────

	def test_unticking_the_damj_clears_what_it_claimed(self):
		paci = self._a_paci(
			damj_is_applicable=1, original_civil_id="299010101010", upload_damj_letter=A_LETTER
		)

		paci.damj_is_applicable = 0
		paci.save()

		self.assertFalse(paci.original_civil_id)
		self.assertFalse(paci.upload_damj_letter)
		self.assertFalse(paci.upload_damj_letter_on)

	def test_unticking_the_fine_puts_the_amount_back_to_zero(self):
		"""Already how set_paci_fine_amount behaved; pinned here with the rest."""
		frappe.db.set_single_value("HR Settings", "paci_fine_amount_kwd", 10)
		paci = self._a_paci(is_paci_fine_applicable=1)
		self.assertEqual(paci.paci_fine_amount_kwd, 10)

		paci.is_paci_fine_applicable = 0
		paci.save()

		self.assertEqual(paci.paci_fine_amount_kwd, 0)

	# ── the letter's timestamp ────────────────────────────────────────────────────

	def test_the_letter_is_stamped_when_it_arrives(self):
		paci = self._a_paci(
			damj_is_applicable=1, original_civil_id="299010101010", upload_damj_letter=A_LETTER
		)

		paci.reload()
		self.assertTrue(paci.upload_damj_letter_on)
