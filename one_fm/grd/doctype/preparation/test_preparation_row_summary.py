# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""What a Preparation row shows about the candidate on it: its Current Stage."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from one_fm import hooks
from one_fm.grd.doctype.preparation.preparation import (
	SUB_DOCUMENT_SEQUENCE,
	create_documents_for_row,
	create_preparation_record,
	current_stage,
	refresh_row_stage,
	update_row_reference,
)

HANDLER = "one_fm.grd.doctype.preparation.preparation.update_row_reference"


def _doc(doctype, state="Draft", docstatus=0, name=None):
	return {
		"doctype": doctype,
		"name": name or doctype.replace(" ", "-") + "-1",
		"workflow_state": state,
		"docstatus": docstatus,
	}


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


class TestCurrentStage(FrappeTestCase):
	def test_no_documents_is_no_stage(self):
		self.assertIsNone(current_stage([]))

	def test_a_document_outside_the_sequence_is_ignored(self):
		self.assertIsNone(current_stage([_doc("Fingerprint Appointment")]))

	def test_the_first_unfinished_document_is_the_stage(self):
		stage = current_stage(
			[_doc("Work Permit", "Completed"), _doc("Medical Insurance", "Draft"), _doc("PACI")]
		)
		self.assertEqual(stage["ref_doctype"], "Medical Insurance")
		self.assertEqual(stage["ref_name"], "Medical-Insurance-1")
		self.assertEqual(stage["ref_doctype_status"], "Medical Insurance - Draft")

	def test_the_order_of_the_input_does_not_matter(self):
		stage = current_stage([_doc("PACI"), _doc("Work Permit")])
		self.assertEqual(stage["ref_doctype"], "Work Permit")

	def test_everything_completed_ends_on_the_last_document(self):
		stage = current_stage([_doc(doctype, "Completed") for doctype in SUB_DOCUMENT_SEQUENCE])
		self.assertEqual(stage["ref_doctype_status"], "PACI - Completed")

	def test_a_cancelled_document_is_labelled_cancelled(self):
		stage = current_stage([_doc("Work Permit", "Completed", docstatus=2)])
		self.assertEqual(stage["ref_doctype_status"], "Work Permit - Cancelled")

	def test_the_label_is_not_translated(self):
		stage = current_stage([_doc("Work Permit", "Apply Online by GR Operator")])
		self.assertEqual(
			stage["ref_doctype_status"], "Work Permit - Apply Online by GR Operator"
		)


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

	# the grid columns

	def test_the_grid_shows_the_current_stage_instead_of_the_row_total(self):
		meta = frappe.get_meta("Preparation Record")
		self.assertFalse(meta.get_field("ref_doctype").in_list_view)
		self.assertTrue(meta.get_field("ref_doctype_status").in_list_view)
		self.assertEqual(meta.get_field("ref_doctype_status").label, "Current Stage")
		self.assertFalse(meta.get_field("total_amount").in_list_view)

	def test_the_status_is_not_the_operator_s_to_type(self):
		meta = frappe.get_meta("Preparation Record")
		for fieldname in ("ref_doctype", "ref_name", "ref_doctype_status"):
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertTrue(field.read_only)
				# Filled in while the Preparation is already submitted.
				self.assertTrue(field.allow_on_submit)

	def test_the_sub_documents_refresh_the_row_on_save_cancel_and_delete(self):
		for doctype in SUB_DOCUMENT_SEQUENCE:
			for event in ("on_update", "on_cancel", "after_delete"):
				with self.subTest(doctype=doctype, event=event):
					self.assertIn(HANDLER, hooks.doc_events[doctype][event])

	# what the row points at

	def test_opening_the_documents_points_the_row_at_the_first_unfinished_one(self):
		preparation = self._a_preparation()

		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		row = self._row(preparation)
		self.assertEqual(row.ref_doctype, "Work Permit")
		self.assertTrue(row.ref_name)
		self.assertTrue(row.ref_doctype_status.startswith("Work Permit - "), row.ref_doctype_status)

	def test_the_status_is_the_document_s_own_state(self):
		preparation = self._a_preparation()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		row = self._row(preparation)
		state = frappe.db.get_value(row.ref_doctype, row.ref_name, "workflow_state")
		self.assertEqual(row.ref_doctype_status, "{0} - {1}".format(row.ref_doctype, state))

	def test_a_row_follows_the_document_when_it_is_cancelled(self):
		preparation = self._a_preparation()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)

		work_permit = frappe.get_last_doc("Work Permit", filters={"preparation": preparation.name})
		frappe.db.set_value("Work Permit", work_permit.name, "docstatus", 2)
		refresh_row_stage(preparation.name, self.employee)

		self.assertEqual(self._row(preparation).ref_doctype_status, "Work Permit - Cancelled")

	def test_refreshing_a_row_with_no_documents_leaves_it_alone(self):
		preparation = self._a_preparation()

		refresh_row_stage(preparation.name, self.employee)

		row = self._row(preparation)
		self.assertFalse(row.ref_doctype)
		self.assertFalse(row.ref_name)
		self.assertFalse(row.ref_doctype_status)

	def test_a_document_with_no_preparation_touches_nothing(self):
		"""Most of these documents are raised outside a Preparation entirely."""
		preparation = self._a_preparation()
		create_documents_for_row(preparation.preparation_record[0], preparation.name)
		before = self._row(preparation).ref_doctype_status

		orphan = frappe.get_last_doc("PACI", filters={"preparation": preparation.name})
		orphan.preparation = None
		update_row_reference(orphan)

		self.assertEqual(self._row(preparation).ref_doctype_status, before)

	def test_the_sequence_is_the_legal_order(self):
		self.assertEqual(
			SUB_DOCUMENT_SEQUENCE, ("Work Permit", "Medical Insurance", "Residency", "PACI")
		)

	# the monthly batch

	def test_the_monthly_batch_is_a_renewal_batch(self):
		"""Auto-generated in Draft, categorised Renewal, named PRE-REN-."""
		before = set(frappe.get_all("Preparation", pluck="name"))

		create_preparation_record()

		created = set(frappe.get_all("Preparation", pluck="name")) - before
		if not created:
			self.skipTest("No employee has a residency expiring next month on this site")

		preparation = frappe.get_doc("Preparation", created.pop())
		self.assertEqual(preparation.category, "Renewal")
		self.assertTrue(preparation.name.startswith("PRE-REN-"), preparation.name)
		self.assertEqual(preparation.docstatus, 0)
