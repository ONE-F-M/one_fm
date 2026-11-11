# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.return_empty_attendance_amendments_to_draft import (
	execute as return_empty_to_draft,
)

EMPTY_TABLE_MESSAGE = "Fetch Attendance Record before submitting for review"


def make_attendance_amendment(project="Empty Table Test Project", month="November", year="2026", rows=0):
	doc = frappe.get_doc(
		{
			"doctype": "Attendance Amendment",
			"project": project,
			"month": month,
			"year": year,
			"attendance_based_on": "Attendance Status",
		}
	)
	for _i in range(rows):
		doc.append("attendance_details", {"employee_name": "Test Employee", "day_1": "Present"})
	doc.flags.ignore_links = True
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


class TestAttendanceAmendment(FrappeTestCase):
	# Each test uses its own month: rollback is per class, and records of one
	# project, site and month may not coexist.
	def test_submit_for_review_with_empty_table_is_refused(self):
		doc = make_attendance_amendment(month="January")
		doc.workflow_state = "Pending Approval"
		with self.assertRaisesRegex(frappe.ValidationError, EMPTY_TABLE_MESSAGE):
			doc.save()
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "workflow_state"), "Draft")

	def test_submit_for_review_with_rows_moves_to_pending_approval(self):
		doc = make_attendance_amendment(month="February", rows=1)
		doc.workflow_state = "Pending Approval"
		doc.save()
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "workflow_state"), "Pending Approval")

	def test_draft_with_empty_table_saves(self):
		doc = make_attendance_amendment(month="March")
		doc.remarks = "part prepared"
		doc.save()
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "remarks"), "part prepared")


class TestReturnEmptyAttendanceAmendmentsToDraft(FrappeTestCase):
	def test_patch_returns_only_empty_records(self):
		# apply_workflow reloads the doc, so link validation runs against a real Project.
		project = frappe.db.get_value("Project", {}, "name")
		if not project:
			self.skipTest("No Project on this site")
		frappe.db.delete("Attendance Amendment", {"project": project, "year": "2029"})

		empty = make_attendance_amendment(project=project, month="November", year="2029")
		filled = make_attendance_amendment(project=project, month="December", year="2029", rows=1)
		for doc in (empty, filled):
			doc.db_set("workflow_state", "Pending Approval", update_modified=False)

		return_empty_to_draft()

		self.assertEqual(frappe.db.get_value(empty.doctype, empty.name, "workflow_state"), "Draft")
		self.assertEqual(frappe.db.get_value(filled.doctype, filled.name, "workflow_state"), "Pending Approval")
		self.assertTrue(
			frappe.db.exists(
				"ToDo",
				{
					"reference_type": empty.doctype,
					"reference_name": empty.name,
					"allocated_to": empty.owner,
					"status": "Open",
				},
			)
		)


class TestAttendanceAmendmentDuplicate(FrappeTestCase):
	"""WI-004528: one live record per project, site, month and year."""

	PROJECT = "Dup Test Project"
	SITE_A = "Dup Test Site A"
	SITE_B = "Dup Test Site B"

	def _new(self, site=None, month="November", year="2026", state=None):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Amendment",
				"project": self.PROJECT,
				"site": site,
				"month": month,
				"year": year,
				"attendance_based_on": "Attendance Status",
			}
		)
		doc.flags.ignore_links = True
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		if state:
			doc.workflow_state = state
		return doc

	def _make(self, site=None, month="November", year="2026", state="Draft"):
		doc = self._new(site=site, month=month, year=year)
		doc.insert()
		# set the state directly: the workflow only allows certain transitions
		doc.db_set("workflow_state", state, update_modified=False)
		return doc

	def test_same_combination_blocked_in_live_states(self):
		for state in ("Draft", "Pending Approval", "Approved"):
			with self.subTest(state=state):
				existing = self._make(site=self.SITE_A, state=state)
				with self.assertRaises(frappe.ValidationError) as ctx:
					self._new(site=self.SITE_A).insert()
				message = str(ctx.exception)
				self.assertIn(existing.name, message)
				self.assertIn(state, message)
				existing.db_set("workflow_state", "Cancelled", update_modified=False)

	def test_cancelled_or_rejected_does_not_block(self):
		for state in ("Cancelled", "Rejected"):
			with self.subTest(state=state):
				self._make(site=self.SITE_A, state=state)
				new = self._new(site=self.SITE_A).insert()
				self.assertTrue(new.name)
				new.db_set("workflow_state", "Cancelled", update_modified=False)

	def test_project_wide_blocks_site_specific(self):
		existing = self._make(site=None)
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._new(site=self.SITE_A).insert()
		self.assertIn(existing.name, str(ctx.exception))

	def test_site_specific_blocks_project_wide(self):
		existing = self._make(site=self.SITE_A)
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._new(site=None).insert()
		self.assertIn(existing.name, str(ctx.exception))

	def test_different_site_does_not_block(self):
		self._make(site=self.SITE_A)
		self.assertTrue(self._new(site=self.SITE_B).insert().name)

	def test_different_month_does_not_block(self):
		self._make(site=self.SITE_A, month="November")
		self.assertTrue(self._new(site=self.SITE_A, month="December").insert().name)

	def test_resaving_own_record_does_not_trip_check(self):
		doc = self._make(site=self.SITE_A)
		doc.reload()
		doc.flags.ignore_links = True
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.remarks = "saved again"
		doc.save()
		self.assertEqual(doc.remarks, "saved again")
