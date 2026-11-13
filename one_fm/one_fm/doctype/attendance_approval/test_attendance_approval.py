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
			"doctype": "Attendance Approval",
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


class TestAttendanceApproval(FrappeTestCase):
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
		frappe.db.delete("Attendance Approval", {"project": project, "year": "2029"})

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


class TestAttendanceApprovalDuplicate(FrappeTestCase):
	"""One live record per project, site, month and year."""

	PROJECT = "Dup Test Project"
	SITE_A = "Dup Test Site A"
	SITE_B = "Dup Test Site B"

	def setUp(self):
		frappe.db.delete("Attendance Approval", {"project": self.PROJECT})

	def _new(self, site=None, month="November", year="2026", state=None):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Approval",
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
				frappe.db.delete("Attendance Approval", {"project": self.PROJECT})
				existing = self._make(site=self.SITE_A, state=state)
				with self.assertRaises(frappe.ValidationError) as ctx:
					self._new(site=self.SITE_A).insert()
				message = str(ctx.exception)
				self.assertIn(existing.name, message)
				self.assertIn(state, message)

	def test_cancelled_or_rejected_does_not_block(self):
		for state in ("Cancelled", "Rejected"):
			with self.subTest(state=state):
				frappe.db.delete("Attendance Approval", {"project": self.PROJECT})
				self._make(site=self.SITE_A, state=state)
				new = self._new(site=self.SITE_A).insert()
				self.assertTrue(new.name)

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


class TestAttendanceApprovalRename(FrappeTestCase):
	"""The rename from Attendance Amendment left nothing pointing at the old names."""

	OLD = ("Attendance Amendment", "Attendance Amendment Item", "Attendance Amendment OT Item")

	def test_old_doctypes_are_gone(self):
		for name in self.OLD:
			self.assertFalse(frappe.db.exists("DocType", name), name)
		for name in ("Attendance Approval", "Attendance Approval Item", "Attendance Approval OT Item"):
			self.assertTrue(frappe.db.exists("DocType", name), name)

	def test_child_rows_carry_new_parenttype(self):
		for child in ("Attendance Approval Item", "Attendance Approval OT Item"):
			self.assertFalse(frappe.db.exists(child, {"parenttype": "Attendance Amendment"}), child)

		doc = make_attendance_amendment(month="April", rows=1)
		self.assertEqual(
			frappe.db.get_value("Attendance Approval Item", {"parent": doc.name}, "parenttype"),
			"Attendance Approval",
		)

	def test_configuration_points_to_new_name(self):
		if frappe.db.exists("Workflow", "Attendance Amendment"):
			self.assertEqual(
				frappe.db.get_value("Workflow", "Attendance Amendment", "document_type"), "Attendance Approval"
			)
		self.assertFalse(frappe.db.exists("Assignment Rule", {"document_type": "Attendance Amendment"}))
		self.assertFalse(frappe.db.exists("Print Format", {"doc_type": "Attendance Amendment"}))
		self.assertFalse(frappe.db.exists("Version", {"ref_doctype": "Attendance Amendment"}))

		field = frappe.db.get_value(
			"Custom Field",
			{"dt": "Sales Invoice", "fieldname": "custom_attendance_amendment"},
			["options", "label"],
			as_dict=True,
		)
		if field:
			self.assertEqual(field.options, "Attendance Approval")
			self.assertEqual(field.label, "Attendance Approval")

	def test_version_changes_load(self):
		from one_fm.one_fm.doctype.attendance_approval.attendance_approval import get_version_changes

		doc = make_attendance_amendment(month="May")
		doc.remarks = "version check"
		# Frappe skips Version rows under tests unless asked.
		doc.save(ignore_version=False)
		changes = get_version_changes(doc.name)
		self.assertTrue(
			any(c["field"] == "remarks" for entry in changes for c in entry["changes"]),
			changes,
		)

	def test_invoice_generation_gate(self):
		from one_fm.one_fm.doctype.attendance_approval.attendance_invoicing import (
			generate_invoice_from_amendment,
		)

		doc = make_attendance_amendment(month="June", rows=1)
		with self.assertRaisesRegex(frappe.ValidationError, "Only Approved Attendance Approvals"):
			generate_invoice_from_amendment(doc.name)

		# An Approved record passes the state gate and stops at the missing contract.
		doc.db_set("workflow_state", "Approved", update_modified=False)
		with self.assertRaisesRegex(frappe.ValidationError, "Please link a Contract"):
			generate_invoice_from_amendment(doc.name)


class TestAttendanceAmendedField(FrappeTestCase):
	def test_new_record_is_not_amended(self):
		field = frappe.get_meta("Attendance Approval").get_field("attendance_amended")
		self.assertEqual(field.fieldtype, "Check")
		self.assertTrue(field.read_only)
		self.assertEqual(make_attendance_amendment(month="July").attendance_amended, 0)
