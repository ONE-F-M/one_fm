# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002093: what a Preparation row shows about the candidate on it."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm.grd.doctype.preparation.preparation import (
	SUB_DOCUMENT_SEQUENCE,
	create_documents_for_row,
	create_preparation_record,
	update_row_reference,
)


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestPreparationRowSummary(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def _a_preparation(self, action="Overseas", category="Onboarding"):
		preparation = frappe.get_doc({
			"doctype": "Preparation",
			"category": category,
			"posting_date": nowdate(),
			"preparation_record": [{"employee": self.employee, "renewal_or_extend": action}],
		})
		preparation.flags.ignore_permissions = True
		preparation.insert()
		return preparation

	def _row(self, preparation):
		return frappe.get_doc("Preparation", preparation.name).preparation_record[0]

	# ── the grid columns ──────────────────────────────────────────────────────────

	def test_the_grid_shows_progress_instead_of_the_row_total(self):
		meta = frappe.get_meta("Preparation Record")
		self.assertTrue(meta.get_field("ref_doctype").in_list_view)
		self.assertTrue(meta.get_field("ref_doctype_status").in_list_view)
		self.assertFalse(meta.get_field("total_amount").in_list_view)

	def test_the_status_is_not_the_operator_s_to_type(self):
		meta = frappe.get_meta("Preparation Record")
		for fieldname in ("ref_doctype", "ref_name", "ref_doctype_status"):
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertTrue(field.read_only)
				# Filled in while the Preparation is already submitted.
				self.assertTrue(field.allow_on_submit)

	# ── what the row points at ────────────────────────────────────────────────────

	def test_opening_the_documents_points_the_row_at_the_furthest_one(self):
		preparation = self._a_preparation()

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		row = self._row(preparation)
		self.assertEqual(row.ref_doctype, "PACI")
		self.assertTrue(row.ref_name)
		self.assertTrue(row.ref_doctype_status)

	def test_the_status_is_the_document_s_own_state(self):
		preparation = self._a_preparation()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		row = self._row(preparation)
		self.assertEqual(
			row.ref_doctype_status,
			frappe.db.get_value(row.ref_doctype, row.ref_name, "workflow_state"),
		)

	def test_a_row_only_ever_moves_forward(self):
		"""An earlier document saving must not pull the row back off the one it reached."""
		preparation = self._a_preparation()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)
		self.assertEqual(self._row(preparation).ref_doctype, "PACI")

		work_permit = frappe.get_last_doc("Work Permit", filters={"preparation": preparation.name})
		update_row_reference(work_permit)

		self.assertEqual(self._row(preparation).ref_doctype, "PACI")

	def test_a_document_with_no_preparation_touches_nothing(self):
		"""Most of these documents are raised outside a Preparation entirely."""
		preparation = self._a_preparation()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)
		before = self._row(preparation).ref_doctype

		orphan = frappe.get_last_doc("PACI", filters={"preparation": preparation.name})
		orphan.preparation = None
		update_row_reference(orphan)

		self.assertEqual(self._row(preparation).ref_doctype, before)

	def test_the_sequence_is_the_legal_order(self):
		self.assertEqual(SUB_DOCUMENT_SEQUENCE, ("Work Permit", "Medical Insurance", "Residency", "PACI"))

	# ── the monthly batch ─────────────────────────────────────────────────────────

	def test_the_monthly_batch_is_a_renewal_batch(self):
		"""Auto-generated in Draft, categorised Renewal, named PRE-REN- (WI-002093)."""
		before = set(frappe.get_all("Preparation", pluck="name"))

		create_preparation_record()

		created = set(frappe.get_all("Preparation", pluck="name")) - before
		if not created:
			self.skipTest("No employee has a residency expiring next month on this site")

		preparation = frappe.get_doc("Preparation", created.pop())
		self.assertEqual(preparation.category, "Renewal")
		self.assertTrue(preparation.name.startswith("PRE-REN-"), preparation.name)
		self.assertEqual(preparation.docstatus, 0)
