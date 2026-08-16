# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001828: raising a fresh Work Permit from one that was rejected."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.grd.doctype.work_permit.work_permit import (
	REJECTED_STATE,
	REJECTION_OUTCOME_FIELDS,
	can_reapply,
	reapply_work_permit,
)


class TestReapplyAfterRejection(FrappeTestCase):
	def setUp(self):
		name = frappe.db.get_value(
			"Work Permit",
			{"docstatus": ["<", 2], "rejected_work_permit": ["is", "not set"]},
			"name",
			order_by="creation desc",
		)
		if not name:
			self.skipTest("no Work Permit on this instance to reapply from")

		self.source = name
		# WorkPermit.cancel_existing() calls frappe.db.commit() in before_insert, so
		# FrappeTestCase's rollback cannot take a reapplication back - it is already
		# committed. Every one this class creates is therefore deleted explicitly.
		self.addCleanup(self._delete_reapplications)

		frappe.db.set_value(
			"Work Permit",
			self.source,
			{
				"workflow_state": REJECTED_STATE,
				"reason_of_rejection": "Rejected by PAM",
				"pam_rejection_reason": "PAM Contract",
				"reference_number_on_pam_registration": "PAM-REF-999",
			},
			update_modified=False,
		)

	def _doc(self):
		return frappe.get_doc("Work Permit", self.source)

	def _delete_reapplications(self):
		for name in frappe.get_all(
			"Work Permit", filters={"rejected_work_permit": self.source}, pluck="name"
		):
			frappe.delete_doc(
				"Work Permit", name, force=True, ignore_permissions=True, delete_permanently=True
			)
		frappe.db.commit()

	def test_only_a_rejected_permit_can_be_reapplied(self):
		self.assertTrue(can_reapply(self._doc()))

		for state in ("Draft", "Pending By PAM", "Completed"):
			frappe.db.set_value("Work Permit", self.source, "workflow_state", state, update_modified=False)
			self.assertFalse(can_reapply(self._doc()), msg=state)

	def test_the_server_refuses_a_permit_that_does_not_qualify(self):
		"""The button is the first gate; the method has to hold on its own."""
		frappe.db.set_value("Work Permit", self.source, "workflow_state", "Draft", update_modified=False)

		with self.assertRaises(frappe.ValidationError):
			reapply_work_permit(self.source)

	def test_the_candidate_comes_across(self):
		source = self._doc()
		new = frappe.get_doc("Work Permit", reapply_work_permit(self.source)["name"])

		self.assertEqual(new.rejected_work_permit, source.name)
		self.assertEqual(new.employee, source.employee)
		self.assertEqual(new.work_permit_type, source.work_permit_type)
		# The AC names the salary and contract details as things to keep.
		self.assertEqual(new.work_permit_salary, source.work_permit_salary)
		self.assertEqual(new.pam_designation, source.pam_designation)
		# And the batch that started it, so the trail back to the Preparation survives.
		self.assertEqual(new.preparation, source.preparation)

	def test_the_failed_attempt_does_not_come_across(self):
		new = frappe.get_doc("Work Permit", reapply_work_permit(self.source)["name"])

		self.assertEqual(new.workflow_state, "Draft")

		for fieldname in REJECTION_OUTCOME_FIELDS:
			# work_permit_approved carries a default of "No", which is exactly "not
			# approved yet" - so it is cleared back to its default rather than to empty.
			expected = frappe.get_meta("Work Permit").get_field(fieldname).default or None
			self.assertEqual(new.get(fieldname) or None, expected, msg=fieldname)

	def test_the_pam_reference_is_cleared(self):
		"""Named by the AC. There are two fields with that label - both go."""
		new = frappe.get_doc("Work Permit", reapply_work_permit(self.source)["name"])

		self.assertFalse(new.reference_number_on_pam_registration)
		self.assertFalse(new.reference_number_on_pam)

	def test_the_new_attempt_is_dated_today(self):
		new = frappe.get_doc("Work Permit", reapply_work_permit(self.source)["name"])

		self.assertEqual(str(new.date_of_application), today())

	def test_the_rejected_permit_is_left_as_the_history(self):
		reapply_work_permit(self.source)

		source = self._doc()
		self.assertEqual(source.workflow_state, REJECTED_STATE)
		self.assertEqual(source.pam_rejection_reason, "PAM Contract")

	def test_the_link_field_is_read_only_and_not_copied_onward(self):
		"""It records which permit this replaced; a copy of a copy must not inherit it."""
		field = frappe.get_meta("Work Permit").get_field("rejected_work_permit")

		self.assertTrue(field.read_only)
		self.assertTrue(field.no_copy)
		self.assertEqual(field.options, "Work Permit")

	def test_the_button_only_appears_on_a_rejected_permit(self):
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", "work_permit", "work_permit.js")
		)

		self.assertIn("frm.doc.workflow_state !== 'Rejected'", source)
		self.assertIn("reapply_work_permit", source)

	def test_it_is_the_only_button_on_a_rejected_permit(self):
		"""Reported from testing: Reapply and the older "Restart Application" both showed
		on Rejected, offering the same thing twice."""
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", "work_permit", "work_permit.js")
		)

		self.assertNotIn("__('Restart Application')", source)
		self.assertNotIn("set_restart_application(frm)", source)
