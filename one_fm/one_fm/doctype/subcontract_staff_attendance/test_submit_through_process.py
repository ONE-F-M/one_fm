# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import generate_hash

from one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance import (
	SUBMIT_TASK,
	save_attendance_records,
	submit_through_process,
)

USER = "ssa-portal-test@example.com"
DOCTYPE = "Subcontract Staff Attendance"


class TestSubmitThroughProcess(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.supplier = frappe.get_all("Supplier", pluck="name", limit=1)[0]
		if not frappe.db.exists("User", USER):
			frappe.get_doc(
				{"doctype": "User", "email": USER, "first_name": "SSA Portal", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "User Permission", "user": USER, "allow": "Supplier", "for_value": cls.supplier}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _instance(self, docname, task_name=SUBMIT_TASK, status="Waiting"):
		name = generate_hash(length=10)
		frappe.get_doc(
			{
				"doctype": "BPMN Process Instance",
				"name": name,
				"status": "Active",
				"context_doctype": DOCTYPE,
				"context_docname": docname,
				"initiated_by": USER,
			}
		).db_insert()
		task_id = generate_hash()
		frappe.get_doc(
			{
				"doctype": "BPMN Active Task",
				"name": generate_hash(length=10),
				"parent": name,
				"parenttype": "BPMN Process Instance",
				"parentfield": "active_tasks",
				"task_id": task_id,
				"task_name": task_name,
				"status": status,
			}
		).db_insert()
		return name, task_id

	def test_another_subcontractors_records_are_refused(self):
		frappe.set_user(USER)
		with self.assertRaises(frappe.PermissionError):
			save_attendance_records("Not My Supplier", "2099-01-01", "2099-01-31", "Attendance Status", "[]")

	def test_the_waiting_submit_task_is_completed_with_submit(self):
		docname = f"SSA-TEST-{generate_hash(length=6)}"
		instance, task_id = self._instance(docname)
		frappe.set_user(USER)
		with patch("one_bpmn.api.instance_api.complete_task") as complete_task:
			submit_through_process(docname)
		complete_task.assert_called_once_with(instance, task_id, frappe.as_json({"action": "Submit"}))

	def test_the_instance_is_shared_with_the_submitter_only(self):
		docname = f"SSA-TEST-{generate_hash(length=6)}"
		instance, _ = self._instance(docname)
		frappe.set_user(USER)
		with patch("one_bpmn.api.instance_api.complete_task"):
			submit_through_process(docname)
		frappe.set_user("Administrator")
		shares = frappe.get_all(
			"DocShare",
			filters={"share_doctype": "BPMN Process Instance", "share_name": instance},
			fields=["user", "write"],
		)
		self.assertEqual([(s.user, s.write) for s in shares], [(USER, 1)])

	def test_a_record_with_no_waiting_submit_task_is_refused(self):
		docname = f"SSA-TEST-{generate_hash(length=6)}"
		self._instance(docname, task_name="Review & Approve Attendance")
		frappe.set_user(USER)
		with patch("one_bpmn.api.instance_api.complete_task") as complete_task:
			with self.assertRaises(frappe.ValidationError):
				submit_through_process(docname)
		complete_task.assert_not_called()
