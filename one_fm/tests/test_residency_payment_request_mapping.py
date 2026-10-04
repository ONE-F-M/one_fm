# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002499: what the reference table holds when a Residency Payment Request is opened."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.residency_payment import REFERENCE_DEFAULTS, reference_rows

# The columns the story says are the finance user's to fill in when the payment is made.
LEFT_BLANK = (
	"supplier",
	"payment_request",
	"payment_entry",
	"mode_of_payment",
	"bank_account",
	"account",
	"payment_reference",
)


def _preparation(rows):
	return frappe._dict(
		doctype="Preparation",
		name="PRE-2025-09-23-583031",
		docstatus=1,
		preparation_record=[frappe._dict(row) for row in rows],
	)


class TestAPreparation(FrappeTestCase):
	def setUp(self):
		self.rows = reference_rows(
			_preparation(
				[
					{"employee": "HR-EMP-00001", "total_amount": 125.5},
					{"employee": "HR-EMP-00002", "total_amount": 60.0},
				]
			)
		)

	def test_one_row_per_employee(self):
		self.assertEqual(len(self.rows), 2)
		self.assertEqual(
			[row["employee"] for row in self.rows], ["HR-EMP-00001", "HR-EMP-00002"]
		)

	def test_every_row_names_the_preparation_not_the_child_row(self):
		"""Twelve employees produce twelve rows all naming the same Preparation, which is
		what makes the payment traceable back to the document that raised it."""
		for row in self.rows:
			self.assertEqual(row["reference_type"], "Preparation")
			self.assertEqual(row["reference_name"], "PRE-2025-09-23-583031")

	def test_the_amount_is_the_rows_total(self):
		self.assertEqual([row["amount"] for row in self.rows], [125.5, 60.0])

	def test_a_row_with_nothing_to_pay_is_not_a_payment(self):
		rows = reference_rows(
			_preparation(
				[
					{"employee": "HR-EMP-00001", "total_amount": 0},
					{"employee": "HR-EMP-00002", "total_amount": 60.0},
					{"employee": None, "total_amount": 40.0},
				]
			)
		)
		self.assertEqual([row["employee"] for row in rows], ["HR-EMP-00002"])


class TestAFine(FrappeTestCase):
	def test_a_residency_produces_one_row_for_its_fine(self):
		rows = reference_rows(
			frappe._dict(
				doctype="Residency",
				name="MOI-2026-00130",
				employee="HR-EMP-00001",
				residency_fine_amount_kwd=10.0,
			)
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["reference_type"], "Residency")
		self.assertEqual(rows[0]["reference_name"], "MOI-2026-00130")
		self.assertEqual(rows[0]["amount"], 10.0)

	def test_a_paci_produces_one_row_for_its_fine(self):
		rows = reference_rows(
			frappe._dict(
				doctype="PACI",
				name="PACI-2026-00131",
				employee="HR-EMP-00001",
				paci_fine_amount_kwd=2.0,
			)
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["reference_type"], "PACI")
		self.assertEqual(rows[0]["reference_name"], "PACI-2026-00131")
		self.assertEqual(rows[0]["amount"], 2.0)

	def test_nothing_else_produces_a_row(self):
		self.assertEqual(reference_rows(frappe._dict(doctype="Work Permit", name="WP-1")), [])


class TestWhatEveryRowSays(FrappeTestCase):
	def setUp(self):
		self.row = reference_rows(
			frappe._dict(
				doctype="PACI",
				name="PACI-2026-00131",
				employee="HR-EMP-00001",
				paci_fine_amount_kwd=2.0,
			)
		)[0]

	def test_it_opens_submitted_and_initiated(self):
		self.assertEqual(self.row["reference_doc_status"], "Submitted")
		self.assertEqual(self.row["payment_status"], "Initiated")

	def test_the_payment_columns_are_left_for_the_finance_user(self):
		"""A default there would read as a decision somebody took."""
		for fieldname in LEFT_BLANK:
			self.assertNotIn(fieldname, self.row)

	def test_the_defaults_are_options_the_fields_offer(self):
		meta = frappe.get_meta("Residency Payment Request Reference")
		for fieldname, value in REFERENCE_DEFAULTS.items():
			self.assertIn(value, meta.get_field(fieldname).options.split("\n"), fieldname)

	def test_every_mapped_field_exists_on_the_child_table(self):
		meta = frappe.get_meta("Residency Payment Request Reference")
		for fieldname in self.row:
			self.assertTrue(meta.get_field(fieldname), fieldname)

	def test_every_mandatory_column_is_filled(self):
		"""The request is handed over unsaved, so a missing one surfaces as a save the
		operator cannot complete rather than as an error they can act on."""
		meta = frappe.get_meta("Residency Payment Request Reference")
		for field in meta.fields:
			if field.reqd:
				self.assertIn(field.fieldname, self.row, field.fieldname)
