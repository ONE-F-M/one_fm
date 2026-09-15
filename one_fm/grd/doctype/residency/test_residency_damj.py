# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002022: the Damj and Residency Fine exception paths on Residency."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

A_LETTER = "/files/damj-letter.pdf"
A_RECEIPT = "/files/fine-receipt.pdf"


def _an_active_employee():
	"""An employee a Residency can be opened for.

	Taken from the site rather than created: Employee sits at MariaDB's row-size limit
	here, so a fixture would need a Company, a Fiscal Year and a Designation before it
	inserted. Same reason test_preparation_new_actions.py does it this way.
	"""
	name = frappe.db.get_value("Employee", {"status": "Active"}, "name", order_by="creation asc")
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestResidencyDamj(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.original_civil_id = frappe.db.get_value("Employee", self.employee, "one_fm_civil_id")

	def _residency(self, **kwargs):
		residency = frappe.get_doc(
			{
				"doctype": "Residency",
				"employee": self.employee,
				"category": "Renewal",
				"date_of_application": today(),
				**kwargs,
			}
		)
		residency.flags.ignore_permissions = True
		return residency

	def test_damj_without_original_civil_id_or_letter_blocks_the_save(self):
		with self.assertRaises(frappe.ValidationError):
			self._residency(damj_is_applicable=1).insert()

	def test_damj_without_the_letter_alone_blocks_the_save(self):
		with self.assertRaises(frappe.ValidationError):
			self._residency(damj_is_applicable=1, original_civil_id="299010112345").insert()

	def test_damj_with_both_saves(self):
		residency = self._residency(
			damj_is_applicable=1,
			original_civil_id="299010112345",
			upload_damj_letter=A_LETTER,
		)
		residency.insert()
		self.assertEqual(residency.original_civil_id, "299010112345")

	def test_fine_without_amount_or_receipt_blocks_the_save(self):
		with self.assertRaises(frappe.ValidationError):
			self._residency(residency_fine_to_be_added=1).insert()

	def test_a_zero_fine_amount_counts_as_missing(self):
		# Ticking the box and entering nothing is the mistake the check exists to catch.
		with self.assertRaises(frappe.ValidationError):
			self._residency(
				residency_fine_to_be_added=1,
				residency_fine_amount_kwd=0,
				upload_residency_fine_payment_receipt=A_RECEIPT,
			).insert()

	def test_fine_with_amount_and_receipt_saves(self):
		residency = self._residency(
			residency_fine_to_be_added=1,
			residency_fine_amount_kwd=15.5,
			upload_residency_fine_payment_receipt=A_RECEIPT,
		)
		residency.insert()
		self.assertEqual(residency.residency_fine_amount_kwd, 15.5)

	def test_neither_box_ticked_needs_nothing(self):
		self._residency().insert()

	def test_completing_a_damj_writes_the_original_civil_id_to_the_employee(self):
		merged = "299010199999"
		residency = self._residency(
			damj_is_applicable=1,
			original_civil_id=merged,
			upload_damj_letter=A_LETTER,
			invoice_attachment="/files/invoice.pdf",
			new_residency_expiry_date=today(),
		)
		residency.insert()
		residency.submit()

		self.assertEqual(frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"), merged)
		# The record that carries the merge must not still show the retired number.
		self.assertEqual(frappe.db.get_value("Residency", residency.name, "one_fm_civil_id"), merged)

	def test_completing_without_damj_leaves_the_employee_civil_id_alone(self):
		residency = self._residency(
			original_civil_id="299010188888",  # populated but the box is not ticked
			invoice_attachment="/files/invoice.pdf",
			new_residency_expiry_date=today(),
		)
		residency.insert()
		residency.submit()

		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "one_fm_civil_id"),
			self.original_civil_id,
		)
