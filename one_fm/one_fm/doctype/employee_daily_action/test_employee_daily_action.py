# # Copyright (c) 2025, ONE FM and Contributors
# # See license.txt

from unittest import mock, TestCase
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase




# class TestEmployeeDailyAction(FrappeTestCase):
# 	pass
# 	def setUp(self):
# 		# Create test employee and manager
# 		self.test_employee = frappe.get_doc({
# 			"doctype": "User",
# 			"email": "test_employee@example.com",
# 			"first_name": "Test",
# 			"last_name": "Employee"
# 		}).insert(ignore_if_duplicate=True)

# 		self.test_manager = frappe.get_doc({
# 			"doctype": "User", 
# 			"email": "test_manager@example.com",
# 			"first_name": "Test",
# 			"last_name": "Manager"
# 		}).insert(ignore_if_duplicate=True)

# 	def test_fetch_todos(self):
# 		# Create test ToDo items for today
# 		todo1 = frappe.get_doc({
# 			"doctype": "ToDo",
# 			"allocated_to": "test_employee@example.com",
# 			"date": frappe.utils.today(),
# 			"description": "Test Todo 1",
# 			"status": "Open",
# 			"type": "General"
# 		}).insert()

# 		todo2 = frappe.get_doc({
# 			"doctype": "ToDo", 
# 			"allocated_to": "test_employee@example.com",
# 			"date": frappe.utils.today(),
# 			"description": "Test Todo 2",
# 			"status": "Closed",
# 			"type": "Technical"
# 		}).insert()

# 		# Create test ToDo items for tomorrow
# 		tomorrow = frappe.utils.add_days(frappe.utils.today(), 1)
# 		todo3 = frappe.get_doc({
# 			"doctype": "ToDo",
# 			"allocated_to": "test_employee@example.com",
# 			"date": tomorrow,
# 			"description": "Test Todo 3",
# 			"status": "Open",
# 			"type": "Project"
# 		}).insert()

# 		todo4 = frappe.get_doc({
# 			"doctype": "ToDo",
# 			"allocated_to": "test_employee@example.com",
# 			"date": tomorrow,
# 			"description": "Test Todo 4",
# 			"status": "Open",
# 			"type": "Routine"
# 		}).insert()

# 		# Create Employee Daily Action
# 		eda = frappe.get_doc({
# 			"doctype": "Employee Daily Action",
# 			"employee_email": "test_employee@example.com",
# 			"manager_email": "test_manager@example.com",
# 			"date": frappe.utils.today()
# 		})
# 		eda.insert()

# 		# Test today's todos were fetched correctly
# 		self.assertEqual(len(eda.todays_plan_and_accomplishments), 2)
# 		today_todo = eda.todays_plan_and_accomplishments[0]
# 		self.assertEqual(today_todo.todo, todo1.name)
# 		self.assertEqual(today_todo.todo_type, "General")
# 		self.assertEqual(today_todo.completed, 0)
# 		self.assertEqual(today_todo.description, "Test Todo 1")

# 		today_todo2 = eda.todays_plan_and_accomplishments[1] 
# 		self.assertEqual(today_todo2.todo, todo2.name)
# 		self.assertEqual(today_todo2.todo_type, "Technical")
# 		self.assertEqual(today_todo2.completed, 1)
# 		self.assertEqual(today_todo2.description, "Test Todo 2")

# 		# Test tomorrow's todos were fetched correctly
# 		self.assertEqual(len(eda.tomorrows_plan), 2)
# 		tomorrow_todo = eda.tomorrows_plan[0]
# 		self.assertEqual(tomorrow_todo.todo, todo3.name)
# 		self.assertEqual(tomorrow_todo.todo_type, "Project")
# 		self.assertEqual(tomorrow_todo.description, "Test Todo 3")

# 		tomorrow_todo2 = eda.tomorrows_plan[1]
# 		self.assertEqual(tomorrow_todo2.todo, todo4.name)
# 		self.assertEqual(tomorrow_todo2.todo_type, "Routine")
# 		self.assertEqual(tomorrow_todo2.description, "Test Todo 4")

# 	def test_create_blockers(self):
# 		# Create Employee Daily Action with blockers
# 		eda = frappe.get_doc({
# 			"doctype": "Employee Daily Action",
# 			"employee_email": "test_employee@example.com", 
# 			"manager_email": "test_manager@example.com",
# 			"date": frappe.utils.today(),
# 			"blocker_table": [
# 				{
# 					"priority": "High",
# 					"problem": "Test Blocker 1"
# 				},
# 				{
# 					"priority": "Medium", 
# 					"problem": "Test Blocker 2"
# 				}
# 			]
# 		})
# 		eda.insert()
# 		eda.submit()

# 		# Verify blockers were created
# 		blockers = frappe.get_all("Blocker", 
# 			filters={
# 				"user": "test_employee@example.com",
# 				"date": frappe.utils.today()
# 			},
# 			fields=["priority", "blocker_details", "status"]
# 		)

# 		self.assertEqual(len(blockers), 2)
# 		self.assertEqual(blockers[0].priority, "High")
# 		self.assertEqual(blockers[0].blocker_details, "Test Blocker 1")
# 		self.assertEqual(blockers[0].status, "Open")

# 	def tearDown(self):
# 		# Clean up test data
# 		frappe.db.sql("delete from `tabToDo` where allocated_to='test_employee@example.com'")
# 		frappe.db.sql("delete from `tabBlocker` where user='test_employee@example.com'")
# 		frappe.delete_doc("User", "test_employee@example.com")
# 		frappe.delete_doc("User", "test_manager@example.com")



class TestNotifyReportsToOnAbsenceOfReport(TestCase):
    def setUp(self):
        self.sendemail_patcher = mock.patch("one_fm.one_fm.doctype.employee_daily_action.employee_daily_action.sendemail")
        self.mock_sendemail = self.sendemail_patcher.start()
        
        self.get_approver_user_patcher = mock.patch("one_fm.one_fm.doctype.employee_daily_action.employee_daily_action.get_approver_user", return_value="approver@example.com")
        self.get_approver_user_patcher.start()
        
        self.get_list_patcher = mock.patch("frappe.db.get_list")
        self.mock_get_list = self.get_list_patcher.start()
        
        self.get_all_patcher = mock.patch("frappe.db.get_all")
        self.mock_get_all = self.get_all_patcher.start()
        
        self.sql_patcher = mock.patch("frappe.db.sql")
        self.mock_sql = self.sql_patcher.start()
        
        self.render_template_patcher = mock.patch("frappe.render_template", return_value="<html>Test Email</html>")
        self.render_template_patcher.start()
        
        self.get_value_patcher = mock.patch("frappe.get_value", return_value="test@example.com")
        self.get_value_patcher.start()
        
        self.yesterday = frappe.utils.add_days(frappe.utils.today(), -1)

    def tearDown(self):
        self.sendemail_patcher.stop()
        self.get_approver_user_patcher.stop()
        self.get_list_patcher.stop()
        self.get_all_patcher.stop()
        self.sql_patcher.stop()
        self.render_template_patcher.stop()
        self.get_value_patcher.stop()

    def _run_notifier(self):
        from one_fm.one_fm.doctype.employee_daily_action.employee_daily_action import NotifyReportsToOnAbsenceOfReport
        notifier = NotifyReportsToOnAbsenceOfReport()
        notifier.notify_employee()

    def test_shift_working_employee_should_notify(self):
        def get_list_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Daily Action":
                return []
            elif doctype == "Employee":
                return [SimpleNamespace(
                    name="EMP-SHIFT-1",
                    employee_name="Shift Employee",
                    shift_working=1,
                    holiday_list=None,
                    attendance_by_timesheet=0
                )]
        
        def get_all_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Schedule":
                return ["EMP-SHIFT-1"]
            elif doctype == "Attendance":
                return []
            return []
        
        self.mock_get_list.side_effect = get_list_side_effect
        self.mock_get_all.side_effect = get_all_side_effect
        self.mock_sql.return_value = []
        
        self._run_notifier()
        
        self.assertTrue(self.mock_sendemail.called)
        call_args = self.mock_sendemail.call_args
        self.assertIn("approver@example.com", call_args[1]["recipients"])

    def test_non_shift_employee_should_notify(self):
        def get_list_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Daily Action":
                return []
            elif doctype == "Employee":
                return [SimpleNamespace(
                    name="EMP-NONSHIFT-1",
                    employee_name="Non-Shift Employee",
                    shift_working=0,
                    holiday_list="HL-2025",
                    attendance_by_timesheet=0
                )]
        
        def get_all_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Schedule":
                return []
            elif doctype == "Attendance":
                return []
            return []
        
        self.mock_get_list.side_effect = get_list_side_effect
        self.mock_get_all.side_effect = get_all_side_effect
        self.mock_sql.return_value = []
        
        self._run_notifier()
        
        self.assertTrue(self.mock_sendemail.called)

    def test_employee_submitted_daily_action_should_not_notify(self):
        def get_list_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Daily Action":
                return ["EMP-SHIFT-2"]
            elif doctype == "Employee":
                return [SimpleNamespace(
                    name="EMP-SHIFT-2",
                    employee_name="Shift Employee 2",
                    shift_working=1,
                    holiday_list=None,
                    attendance_by_timesheet=0
                )]
        
        self.mock_get_list.side_effect = get_list_side_effect
        self.mock_get_all.return_value = []
        self.mock_sql.return_value = []
        
        self._run_notifier()
        
        self.assertFalse(self.mock_sendemail.called)

    def test_non_shift_employee_on_leave_should_not_notify(self):
        def get_list_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Daily Action":
                return []
            elif doctype == "Employee":
                return [SimpleNamespace(
                    name="EMP-NONSHIFT-2",
                    employee_name="Non-Shift Employee 2",
                    shift_working=0,
                    holiday_list="HL-2025",
                    attendance_by_timesheet=0
                )]
        
        def get_all_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Schedule":
                return []
            elif doctype == "Attendance":
                return ["EMP-NONSHIFT-2"]
            return []
        
        self.mock_get_list.side_effect = get_list_side_effect
        self.mock_get_all.side_effect = get_all_side_effect
        self.mock_sql.return_value = []
        
        self._run_notifier()
        
        self.assertFalse(self.mock_sendemail.called)

    def test_non_shift_employee_on_holiday_should_not_notify(self):
        def get_list_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Daily Action":
                return []
            elif doctype == "Employee":
                return [SimpleNamespace(
                    name="EMP-NONSHIFT-3",
                    employee_name="Non-Shift Employee 3",
                    shift_working=0,
                    holiday_list="HL-2025",
                    attendance_by_timesheet=0
                )]
        
        def get_all_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Schedule":
                return []
            elif doctype == "Attendance":
                return []
            return []
        
        self.mock_get_list.side_effect = get_list_side_effect
        self.mock_get_all.side_effect = get_all_side_effect
        self.mock_sql.return_value = [("HL-2025",)]
        
        self._run_notifier()
        
        self.assertFalse(self.mock_sendemail.called)

    def test_shift_employee_not_scheduled_should_not_notify(self):
        def get_list_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Daily Action":
                return []
            elif doctype == "Employee":
                return [SimpleNamespace(
                    name="EMP-SHIFT-3",
                    employee_name="Shift Employee 3",
                    shift_working=1,
                    holiday_list=None,
                    attendance_by_timesheet=0
                )]
        
        def get_all_side_effect(doctype, filters=None, pluck=None, fields=None):
            if doctype == "Employee Schedule":
                return []
            elif doctype == "Attendance":
                return []
            return []
        
        self.mock_get_list.side_effect = get_list_side_effect
        self.mock_get_all.side_effect = get_all_side_effect
        self.mock_sql.return_value = []
        
        self._run_notifier()
        
        self.assertFalse(self.mock_sendemail.called)


class TestTodaysPlanReferenceValidation(FrappeTestCase):
	"""HD-1879549: the `reference` column of Todays Plan and Accomplishments holds a
	document name copied from ToDo.reference_name, not a person's name.

	It was once a Data field with `options = "Name"`, which makes Frappe run
	`frappe.utils.validate_name()` over it (see BaseDocument._validate_data_fields).
	That validator only accepts letters, digits, underscore, apostrophe, hyphen and
	single spaces, so any ToDo pointing at a Contract, a Roster Employee Action or a
	Default Shift Checker blocked the whole Employee Daily Action from being saved
	with "<name> is not a valid Name".

	Do not give this field a `options` validator again.
	"""

	# real production document names that the "Name" validator rejected
	DOCUMENT_NAMES = [
		"Reem Hotel Management & Real Estate Service Co. W.L.L.-Reem Hotel - Alshuwaikh-",
		"WTE O&M Kuwait Sewage Treatment S.P.C.-WTE - 1820-",
		"2026-11-01|2026-11-30|HR-EMP-03965-1884253",
	]

	def test_reference_field_has_no_name_validator(self):
		reference = frappe.get_meta("Todays Plan and Accomplishments").get_field("reference")
		self.assertFalse(
			reference.options,
			"`reference` holds a document name — an `options` validator rejects legitimate names",
		)

	def test_document_names_are_rejected_by_the_name_validator(self):
		"""Pins why the fix matters: every name above fails `validate_name()`, so
		re-adding the validator brings the save blocker straight back."""
		for document_name in self.DOCUMENT_NAMES:
			with self.subTest(document_name=document_name):
				self.assertFalse(frappe.utils.validate_name(document_name))

	def test_document_names_pass_validation(self):
		for document_name in self.DOCUMENT_NAMES:
			with self.subTest(document_name=document_name):
				row = frappe.new_doc("Todays Plan and Accomplishments")
				row.reference_type = "Contracts"
				row.reference = document_name
				row._validate_data_fields()
