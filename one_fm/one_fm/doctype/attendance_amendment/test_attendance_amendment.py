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
