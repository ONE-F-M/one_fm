# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from one_fm.api.tasks import update_shift_assignment_from_permission
employees = frappe.get_test_records('Employee')
class TestShiftPermission(unittest.TestCase):

    def setUp(self):
        # Create Employee
        
        self.employee = frappe.get_doc({
            "doctype": "Employee",
            "employee_name": "Test Employee",
            "status": "Active",
            "company": frappe.defaults.get_user_default("Company") or "Test Company"
        }).insert(ignore_permissions=True)

        # Create Shift Type
        self.shift_type = frappe.get_doc({
            "doctype": "Shift Type",
            "shift_type_name": "Test Shift Type",
            "start_time": "08:00:00",
            "end_time": "17:00:00"
        }).insert(ignore_permissions=True)

        # Create Shift Assignment
        self.today = frappe.utils.today()
        self.shift_assignment = frappe.get_doc({
            "doctype": "Shift Assignment",
            "employee": self.employee.name,
            "shift_type": self.shift_type.name,
            "start_date": self.today,
            "status": "Active",
            "company": self.employee.company
        }).insert(ignore_permissions=True)
        self.shift_assignment.reload()

    def tearDown(self):
        # Clean up created records
        frappe.delete_doc("Shift Assignment", self.shift_assignment.name, ignore_permissions=True)
        frappe.delete_doc("Shift Type", self.shift_type.name, ignore_permissions=True)
        frappe.delete_doc("Employee", self.employee.name, ignore_permissions=True)
        frappe.db.commit()

    def test_update_shift_assignment_start_datetime(self):
        # Create Shift Permission (IN)
        arrival_time = "09:00:00"
        shift_permission = frappe.get_doc({
            "doctype": "Shift Permission",
            "employee": self.employee.name,
            "date": self.today,
            "roster_type": "Basic",
            "shift_type": self.shift_type.name,
            "assigned_shift": self.shift_assignment.name,
            "arrival_time": arrival_time,
            "log_type": "IN",
            "docstatus": 1
        }).insert(ignore_permissions=True)

        # Prepare roster (simulate what your app passes)
        class DummyRoster:
            def __init__(self, employee):
                self.employee = employee
                self.start_datetime = None
                self.end_datetime = None

        roster = [DummyRoster(self.employee.name)]

        # Call the function
        update_shift_assignment_from_permission(roster)

        # Reload and assert
        self.shift_assignment.reload()
        self.assertEqual(
            self.shift_assignment.start_datetime.strftime("%H:%M:%S"),
            arrival_time
        )

    def test_update_shift_assignment_end_datetime(self):
        # Create Shift Permission (OUT)
        leaving_time = "16:30:00"
        shift_permission = frappe.get_doc({
            "doctype": "Shift Permission",
            "employee": self.employee.name,
            "date": self.today,
            "roster_type": "Basic",
            "shift_type": self.shift_type.name,
            "assigned_shift": self.shift_assignment.name,
            "leaving_time": leaving_time,
            "log_type": "OUT",
            "docstatus": 1
        }).insert(ignore_permissions=True)

        # Prepare roster (simulate what your app passes)
        class DummyRoster:
            def __init__(self, employee):
                self.employee = employee
                self.start_datetime = None
                self.end_datetime = None

        roster = [DummyRoster(self.employee.name)]

        # Call the function
        update_shift_assignment_from_permission(roster)

        # Reload and assert
        self.shift_assignment.reload()
        self.assertEqual(
            self.shift_assignment.end_datetime.strftime("%H:%M:%S"),
            leaving_time
        )
	