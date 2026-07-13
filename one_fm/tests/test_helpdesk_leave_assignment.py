# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE-F-M and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from one_fm.overrides import leave_application as la
from one_fm.overrides.leave_application import (
    assign_leave_to_helpdesk_user,
    get_helpdesk_user,
    is_assigned_to_helpdesk_user,
    manage_helpdesk_leave_assignments,
    maybe_assign_helpdesk_on_approval,
    unassign_leave_from_helpdesk_user,
)

HELPDESK_EMAIL = "helpdesk_test@example.com"


class TestHelpDeskLeaveAssignment(unittest.TestCase):
    def setUp(self):
        frappe.flags.in_test = 1
        frappe.set_user("Administrator")
        frappe.flags.ignore_permissions = True

        # Silence outgoing mail during tests. Assignment/unassignment emails are
        # produced by the framework's built-in assignment notification, but
        # these mocks guard against any accidental real send if that path runs
        # inline.
        patcher = patch.object(la, "sendemail")
        self.mock_sendemail = patcher.start()
        self.addCleanup(patcher.stop)

        frappe_patcher = patch("frappe.sendmail")
        self.mock_frappe_sendmail = frappe_patcher.start()
        self.addCleanup(frappe_patcher.stop)

        self.cleanup_test_data()

        self.company = frappe.db.get_value("Company", {"is_group": 0}, "name") or "Test Company"

        # HelpDesk User account + HR Settings pointing at it.
        if not frappe.db.exists("User", HELPDESK_EMAIL):
            frappe.get_doc({
                "doctype": "User",
                "email": HELPDESK_EMAIL,
                "first_name": "HelpDesk",
                "enabled": 1,
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        self.previous_helpdesk_email = frappe.db.get_single_value("HR Settings", "helpdesk_email")
        frappe.db.set_single_value("HR Settings", "helpdesk_email", HELPDESK_EMAIL)

        existing_department = frappe.get_all(
            "Department",
            filters={"department_name": "Test Department", "company": self.company},
            limit=1,
        )
        if existing_department:
            self.department = frappe.get_doc("Department", existing_department[0].name)
        else:
            self.department = frappe.get_doc({
                "doctype": "Department",
                "department_name": "Test Department",
                "department_code": "TESTDEPT",
                "company": self.company,
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("Leave Type", "Annual Leave"):
            self.leave_type = frappe.get_doc({
                "doctype": "Leave Type",
                "leave_type_name": "Annual Leave",
                "is_annual_leave": 1,
                "allow_negative": 0,
                "include_holiday": 0,
            }).insert(ignore_permissions=True)
        else:
            self.leave_type = frappe.get_doc("Leave Type", "Annual Leave")

        # A reliever is mandatory for Annual Leave in this app, so every test
        # leave application is created with this shared reliever employee.
        self.reliever_employee = self.create_employee("HD Reliever", shift_working=0, is_reliever=1)
        self.shift_employee = self.create_employee("HD Shift Employee", shift_working=1)
        self.non_shift_employee = self.create_employee("HD Non Shift Employee", shift_working=0)

        frappe.db.commit()

    def cleanup_test_data(self):
        # IMPORTANT: only ever delete data belonging to THIS test's own
        # employees. Never use a broad "employee LIKE 'HR-EMP-%'" filter — that
        # matches every real employee and would wipe production data, since
        # bench run-tests executes against the live site database.
        test_employees = frappe.get_all(
            "Employee",
            filters={"employee_name": ["in", ["HD Shift Employee", "HD Non Shift Employee", "HD Reliever"]]},
            pluck="name",
        )
        if test_employees:
            frappe.db.delete("Leave Allocation", {"employee": ["in", test_employees]})
            frappe.db.delete("Leave Application", {"employee": ["in", test_employees]})
        frappe.db.delete(
            "ToDo",
            {"reference_type": "Leave Application", "allocated_to": HELPDESK_EMAIL},
        )
        for emp in test_employees:
            frappe.delete_doc("Employee", emp, force=1, ignore_permissions=True)

        for dept in frappe.get_all(
            "Department", filters={"department_name": "Test Department"}, pluck="name"
        ):
            frappe.delete_doc("Department", dept, force=1, ignore_permissions=True)
        frappe.db.commit()

    def create_employee(self, name, shift_working=0, is_reliever=0):
        employee = frappe.get_doc({
            "doctype": "Employee",
            "first_name": name,
            "last_name": "Test",
            "employee_name": name,
            "one_fm_first_name_in_arabic": "اسم",
            "one_fm_last_name_in_arabic": "عائلة",
            "status": "Active",
            "date_of_birth": "1990-01-01",
            "date_of_joining": add_days(today(), -365),
            "gender": "Male",
            "company": self.company,
            "department": self.department.name,
            "annual_leave_balance": 30,
            "day_off_category": "Weekly",
            "number_of_days_off": 1,
            "one_fm_basic_salary": 100,
            "shift_working": shift_working,
            "custom_is_reliever": is_reliever,
            "one_fm_provide_accommodation_by_company": 0,
            "create_user_permission": 0,
        }).insert(ignore_permissions=True)

        leave_allocation = frappe.get_doc({
            "doctype": "Leave Allocation",
            "employee": employee.name,
            "leave_type": self.leave_type.name,
            "from_date": add_days(today(), -365),
            "to_date": add_days(today(), 365),
            "new_leaves_allocated": 30,
        }).insert(ignore_permissions=True)
        leave_allocation.submit()

        return employee

    def create_leave_application(self, employee, resumption_date):
        leave_app = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": employee,
            "leave_type": self.leave_type.name,
            "from_date": add_days(resumption_date, -5),
            "to_date": add_days(resumption_date, -1),
            "resumption_date": resumption_date,
            "custom_reliever_": self.reliever_employee.name,
            "status": "Approved",
        }).insert(ignore_permissions=True)
        leave_app.submit()
        return leave_app

    # --- get_helpdesk_user --------------------------------------------------

    def test_get_helpdesk_user_resolves_configured_email(self):
        self.assertEqual(get_helpdesk_user(), HELPDESK_EMAIL)

    def test_get_helpdesk_user_none_when_unset(self):
        frappe.db.set_single_value("HR Settings", "helpdesk_email", "")
        self.assertIsNone(get_helpdesk_user())

    def test_get_helpdesk_user_none_when_no_user_account(self):
        frappe.db.set_single_value("HR Settings", "helpdesk_email", "nouser@example.com")
        self.assertIsNone(get_helpdesk_user())

    # --- scheduled assignment (exactly 7 days out) --------------------------

    def test_assign_shift_worker_seven_days_before_resumption(self):
        resumption = add_days(getdate(today()), 7)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        manage_helpdesk_leave_assignments()

        self.assertTrue(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    def test_no_assign_for_non_shift_worker(self):
        resumption = add_days(getdate(today()), 7)
        leave = self.create_leave_application(self.non_shift_employee.name, resumption)
        frappe.db.commit()

        manage_helpdesk_leave_assignments()

        self.assertFalse(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    def test_no_assign_when_not_seven_days_out(self):
        resumption = add_days(getdate(today()), 5)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        manage_helpdesk_leave_assignments()

        self.assertFalse(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    def test_assignment_is_idempotent(self):
        resumption = add_days(getdate(today()), 7)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        manage_helpdesk_leave_assignments()
        manage_helpdesk_leave_assignments()

        todos = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "Leave Application",
                "reference_name": leave.name,
                "allocated_to": HELPDESK_EMAIL,
                "status": "Open",
            },
        )
        self.assertEqual(len(todos), 1)

    # --- immediate assignment on approval -----------------------------------

    def test_immediate_assign_on_approval_within_window(self):
        resumption = add_days(getdate(today()), 3)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        maybe_assign_helpdesk_on_approval(leave)

        self.assertTrue(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    def test_no_immediate_assign_outside_window(self):
        resumption = add_days(getdate(today()), 20)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        maybe_assign_helpdesk_on_approval(leave)

        self.assertFalse(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    # --- unassignment -------------------------------------------------------

    def test_unassign_after_resumption_passes(self):
        resumption = add_days(getdate(today()), 7)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        assign_leave_to_helpdesk_user(leave, HELPDESK_EMAIL)
        self.assertTrue(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

        # Move the resumption date into the past and run the scheduler.
        frappe.db.set_value(
            "Leave Application", leave.name, "resumption_date", add_days(getdate(today()), -1)
        )
        frappe.db.commit()

        manage_helpdesk_leave_assignments()

        self.assertFalse(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    def test_unassign_on_cancellation(self):
        resumption = add_days(getdate(today()), 7)
        leave = self.create_leave_application(self.shift_employee.name, resumption)
        frappe.db.commit()

        assign_leave_to_helpdesk_user(leave, HELPDESK_EMAIL)
        self.assertTrue(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

        unassign_leave_from_helpdesk_user(leave, reason="cancelled")

        self.assertFalse(is_assigned_to_helpdesk_user(leave.name, HELPDESK_EMAIL))

    def tearDown(self):
        employees = [self.reliever_employee, self.shift_employee, self.non_shift_employee]
        employee_names = [emp.name for emp in employees]
        for emp in employees:
            frappe.db.sql(
                "DELETE FROM `tabToDo` WHERE reference_type='Leave Application' "
                "AND reference_name IN (SELECT name FROM `tabLeave Application` WHERE employee=%s)",
                (emp.name,),
            )
        frappe.db.sql(
            "DELETE FROM `tabLeave Allocation` WHERE employee IN %s",
            (employee_names,),
        )
        frappe.db.sql(
            "DELETE FROM `tabLeave Application` WHERE employee IN %s",
            (employee_names,),
        )
        for emp in employees:
            if frappe.db.exists("Employee", emp.name):
                frappe.delete_doc("Employee", emp.name, force=1)

        frappe.db.set_single_value("HR Settings", "helpdesk_email", self.previous_helpdesk_email)

        for dept in frappe.get_all(
            "Department", filters={"department_name": "Test Department"}, pluck="name"
        ):
            frappe.delete_doc("Department", dept, force=1, ignore_permissions=True)

        frappe.db.commit()
