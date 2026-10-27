import json
from unittest.mock import patch

import frappe
from frappe.desk.doctype.todo.todo import ToDo
from frappe.tests.utils import FrappeTestCase

from one_fm.api.v1.processa import apply_document_action, get_document_actions

GET_TASKS = "one_bpmn.api.instance_api.get_active_bpmn_tasks"
COMPLETE_TASK = "one_bpmn.api.instance_api.complete_task"
OTHER_USER = "test-processa-other@example.com"


def _task(task_id="TASK-1", can_action=True, details=None, assigned_user="", assigned_role=""):
	return {
		"instance_name": "INST-1",
		"task_id": task_id,
		"task_name": "Review",
		"task_actions": "",
		"task_actions_detail": details if details is not None else [{"action": "Approve"}],
		"assigned_user": assigned_user,
		"assigned_role": assigned_role,
		"can_action": can_action,
	}


class TestProcessaDocumentActions(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", OTHER_USER):
			frappe.get_doc(
				{"doctype": "User", "email": OTHER_USER, "first_name": "Processa Other", "send_welcome_email": 0}
			).insert()

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.todo = frappe.get_doc(
			{"doctype": "ToDo", "description": "Before", "allocated_to": "Administrator"}
		).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_only_tasks_the_user_can_act_on_become_actions(self):
		tasks = [
			_task(details=[{"action": "Approve", "confirmTransition": "true"}, {"action": "Reject"}]),
			_task(task_id="TASK-2", can_action=False, assigned_user="Administrator"),
			_task(task_id="TASK-3", can_action=False, assigned_role="HR Manager"),
		]
		with patch(GET_TASKS, return_value=tasks):
			result = get_document_actions("ToDo", self.todo.name)

		self.assertEqual(
			[(a["task_id"], a["action"], a["confirm"]) for a in result["actions"]],
			[("TASK-1", "Approve", True), ("TASK-1", "Reject", False)],
		)
		self.assertEqual(result["pending_with"], ["Administrator", "HR Manager"])
		self.assertEqual(result["editable_fields"], [])

	def test_a_task_without_configured_actions_gives_one_confirmed_entry(self):
		with patch(GET_TASKS, return_value=[_task(details=[])]):
			result = get_document_actions("ToDo", self.todo.name)

		self.assertEqual(len(result["actions"]), 1)
		self.assertEqual(result["actions"][0]["action"], "")
		self.assertTrue(result["actions"][0]["confirm"])

	def test_a_user_who_cannot_read_the_document_is_refused(self):
		with patch(GET_TASKS, return_value=[_task()]), patch(COMPLETE_TASK) as complete_task:
			frappe.set_user(OTHER_USER)
			with self.assertRaises(frappe.PermissionError):
				get_document_actions("ToDo", self.todo.name)
			with self.assertRaises(frappe.PermissionError):
				apply_document_action("ToDo", self.todo.name, "TASK-1", "Approve")

		complete_task.assert_not_called()

	def test_an_action_the_map_does_not_offer_is_refused(self):
		with patch(GET_TASKS, return_value=[_task()]), patch(COMPLETE_TASK) as complete_task:
			with self.assertRaises(frappe.PermissionError):
				apply_document_action("ToDo", self.todo.name, "TASK-1", "Delete")
			with self.assertRaises(frappe.PermissionError):
				apply_document_action("ToDo", self.todo.name, "TASK-9", "Approve")

		complete_task.assert_not_called()

	def test_an_action_completes_the_task_on_the_server_side_instance(self):
		with patch(GET_TASKS, return_value=[_task()]), patch(
			COMPLETE_TASK, return_value={"status": "Active"}
		) as complete_task:
			apply_document_action("ToDo", self.todo.name, "TASK-1", "Approve")

		complete_task.assert_called_once_with("INST-1", "TASK-1", json.dumps({"action": "Approve"}))

	def test_a_field_the_step_does_not_allow_is_refused_and_not_saved(self):
		with patch(GET_TASKS, return_value=[_task()]), patch(COMPLETE_TASK) as complete_task:
			with self.assertRaises(frappe.PermissionError):
				apply_document_action(
					"ToDo", self.todo.name, "TASK-1", "Approve", values={"description": "After"}
				)

		complete_task.assert_not_called()
		self.assertEqual(frappe.db.get_value("ToDo", self.todo.name, "description"), "Before")

	def test_editable_values_are_saved_before_the_task_completes(self):
		saved_when_completed = []

		def complete(*args):
			saved_when_completed.append(frappe.db.get_value("ToDo", self.todo.name, "description"))
			return {"status": "Active"}

		with patch(GET_TASKS, return_value=[_task()]), patch(COMPLETE_TASK, side_effect=complete), patch.object(
			ToDo, "get_processa_editable_fields", create=True, return_value=["description"]
		):
			result = apply_document_action(
				"ToDo", self.todo.name, "TASK-1", "Approve", values=json.dumps({"description": "After"})
			)

		self.assertEqual(saved_when_completed, ["After"])
		self.assertEqual(result["editable_fields"], ["description"])

	def test_a_permission_error_from_the_engine_reaches_the_caller(self):
		with patch(GET_TASKS, return_value=[_task()]), patch(
			COMPLETE_TASK, side_effect=frappe.PermissionError("Not assigned")
		):
			with self.assertRaises(frappe.PermissionError):
				apply_document_action("ToDo", self.todo.name, "TASK-1", "Approve")

	def test_map_messages_and_process_status_come_back(self):
		def complete(*args):
			frappe.msgprint("Fix the relieving date")
			return {"status": "Errored"}

		with patch(GET_TASKS, return_value=[_task()]), patch(COMPLETE_TASK, side_effect=complete):
			result = apply_document_action("ToDo", self.todo.name, "TASK-1", "Approve")

		self.assertIn("Fix the relieving date", result["messages"])
		self.assertEqual(result["process_status"], "Errored")
