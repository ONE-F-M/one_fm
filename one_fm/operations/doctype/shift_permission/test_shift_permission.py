# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from one_fm.api.tasks import update_shift_assignment_from_permission
from one_fm.tests.test_records import get_holiday_list_and_company,get_sample_employees,get_salary_components,get_salary_structure
from frappe.model.naming import NamingSeries 
company_data = get_holiday_list_and_company()
employee_data = get_sample_employees()
salary_component_data = get_salary_components()
salary_structure_data = get_salary_structure()

frappe.local.flags.ignore_chart_of_accounts = 1

class TestShiftPermission(unittest.TestCase):
    def create_salary_components(self):
        for each in salary_component_data:
            if frappe.db.exists("Salary Component",each.get('salary_component')):
                frappe.delete_doc("Salary Component",each.get('salary_component'),force=1)
            frappe.get_doc(each).insert(ignore_permissions=True)

    def create_salary_structure(self):
        for each in salary_structure_data:
            if frappe.db.exists("Salary Structure",each.get('name')):
                frappe.delete_doc("Salary Structure",each.get('name'),force=1)
            frappe.get_doc(each).insert(ignore_permissions=True)
        

    def setUp(self):

        # Create Dependencies
        shift_1_start_time = "08:00:00"
        shift_1_end_time = "17:00:00"
        shift_2_start_time = "18:00:00"
        shift_2_end_time = "06:00:00"
        for each in company_data:
            if each.get("doctype") == "Holiday List":
                if  frappe.db.exists("Holiday List",each.get('holiday_list_name')):
                    frappe.delete_doc("Holiday List",each.get('holiday_list_name'),force=1)
                frappe.get_doc(each).insert(ignore_permissions=True)
            elif each.get("doctype") == "Company":
                if frappe.db.exists("Company",each.get('company_name')):
                    frappe.delete_doc("Company",each.get('company_name'),force=1)
                frappe.get_doc(each).insert(ignore_permissions=True)
        
        self.create_salary_components()
        if employee_data:
            
            naming_series = employee_data[0].get('naming_series')
            employee_naming_series = NamingSeries(naming_series)
            employee_naming_series.update_counter(1) #Ensure that the counter always starts from 1
            for one in employee_data:
                emp = frappe.get_doc(one)
                emp.flags.ignore_validate = True
                emp.insert(ignore_permissions=True)
            


        
        
        # Create Shift Type
            self.shift_type_1 = frappe.get_doc({
                "doctype": "Shift Type",
                "shift_type_name": "Test Shift Type",
                "start_time": "08:00:00",
                "shift_type":"Day",
                "end_time": "17:00:00"
            }).insert(ignore_permissions=True)

            # Create Shift Assignment
            self.today = frappe.utils.today()
            self.shift_assignment_1 = frappe.get_doc({
                "doctype": "Shift Assignment",
                "employee": 'HR-EMP-00001',
                "shift_type": self.shift_type_1.name,
                "start_date": frappe.utils.today(),
                "start_datetime": frappe.utils.get_datetime(frappe.utils.today() +' '+ shift_1_start_time),
                "end_datetime": frappe.utils.get_datetime(frappe.utils.today() +' '+ shift_2_end_time),
                "status": "Active",
                "company": "_Test Company"
            }).insert(ignore_permissions=True)
            self.shift_assignment_1.reload()

    def tearDown(self):
        # Clean up created records
        frappe.delete_doc("Shift Assignment", self.shift_assignment_1.name, ignore_permissions=True)
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
            "assigned_shift": self.shift_assignment_1.name,
            "leaving_time": leaving_time,
            "log_type": "OUT",
            "docstatus": 1
        }).insert(ignore_permissions=True)

    #     # Prepare roster (simulate what your app passes)
        class DummyRoster:
            def __init__(self, employee):
                self.employee = employee
                self.start_datetime = None
                self.end_datetime = None

        roster = [DummyRoster(self.employee.name)]

        # Call the function
        update_shift_assignment_from_permission(roster)

        # Reload and assert
        self.shift_assignment_1.reload()
        self.assertEqual(
            self.shift_assignment_1.end_datetime.strftime("%H:%M:%S"),
            leaving_time
        )
	