# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002105: which Residency fields show, which are required, and what unticking clears."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

DAMJ = "eval:doc.damj_is_applicable == 1"
FINE = "eval:doc.residency_fine_to_be_added == 1"

A_LETTER = "/files/damj-letter.pdf"
A_RECEIPT = "/files/fine-receipt.pdf"


def _an_active_employee():
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestResidencyExceptionFields(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.meta = frappe.get_meta("Residency")

	def _a_residency(self, **kwargs):
		residency = frappe.get_doc({
			"doctype": "Residency",
			"employee": self.employee,
			"category": "Renewal",
			"date_of_application": today(),
			**kwargs,
		})
		residency.flags.ignore_permissions = True
		residency.insert()
		return residency

	# ── visibility ────────────────────────────────────────────────────────────────

	def test_apply_for_is_off_the_form(self):
		self.assertTrue(self.meta.get_field("apply_for").hidden)

	def test_the_damj_details_follow_the_damj_checkbox(self):
		for fieldname in ("original_civil_id", "upload_damj_letter"):
			with self.subTest(fieldname=fieldname):
				field = self.meta.get_field(fieldname)
				self.assertEqual(field.depends_on, DAMJ)
				self.assertEqual(field.mandatory_depends_on, DAMJ)

	def test_the_fine_details_follow_the_fine_checkbox(self):
		for fieldname in ("residency_fine_amount_kwd", "upload_residency_fine_payment_receipt"):
			with self.subTest(fieldname=fieldname):
				field = self.meta.get_field(fieldname)
				self.assertEqual(field.depends_on, FINE)
				self.assertEqual(field.mandatory_depends_on, FINE)

	def test_a_fine_cannot_be_a_credit(self):
		self.assertTrue(self.meta.get_field("residency_fine_amount_kwd").non_negative)

	# ── required when ticked ──────────────────────────────────────────────────────

	def test_a_ticked_damj_needs_its_civil_id_and_letter(self):
		with self.assertRaises(frappe.ValidationError):
			self._a_residency(damj_is_applicable=1)

	def test_a_ticked_damj_with_both_saves(self):
		residency = self._a_residency(
			damj_is_applicable=1, original_civil_id="299010101010", upload_damj_letter=A_LETTER
		)
		self.assertEqual(residency.original_civil_id, "299010101010")

	def test_a_ticked_fine_needs_an_amount_and_a_receipt(self):
		with self.assertRaises(frappe.ValidationError):
			self._a_residency(residency_fine_to_be_added=1)

	def test_a_ticked_fine_of_zero_is_not_a_fine(self):
		with self.assertRaises(frappe.ValidationError):
			self._a_residency(
				residency_fine_to_be_added=1,
				residency_fine_amount_kwd=0,
				upload_residency_fine_payment_receipt=A_RECEIPT,
			)

	# ── cleared when unticked ─────────────────────────────────────────────────────

	def test_unticking_the_damj_clears_what_it_claimed(self):
		residency = self._a_residency(
			damj_is_applicable=1, original_civil_id="299010101010", upload_damj_letter=A_LETTER
		)

		residency.damj_is_applicable = 0
		residency.save()

		self.assertFalse(residency.original_civil_id)
		self.assertFalse(residency.upload_damj_letter)
		self.assertFalse(residency.upload_damj_letter_on)

	def test_unticking_the_fine_puts_the_amount_back_to_zero(self):
		residency = self._a_residency(
			residency_fine_to_be_added=1,
			residency_fine_amount_kwd=25,
			upload_residency_fine_payment_receipt=A_RECEIPT,
		)

		residency.residency_fine_to_be_added = 0
		residency.save()

		self.assertEqual(residency.residency_fine_amount_kwd, 0)
		self.assertFalse(residency.upload_residency_fine_payment_receipt)
		self.assertFalse(residency.upload_residency_fine_payment_receipt_on)

	def test_a_record_that_never_claimed_either_is_left_alone(self):
		residency = self._a_residency()

		self.assertFalse(residency.original_civil_id)
		self.assertEqual(residency.residency_fine_amount_kwd, 0)
