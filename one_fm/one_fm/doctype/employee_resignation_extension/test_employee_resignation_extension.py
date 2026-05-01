# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

class TestEmployeeResignationExtension(FrappeTestCase):
    def setUp(self):
        # Create dummy Employee
        if not frappe.db.exists("Employee", "HR-EMP-EXT-01"):
            emp = frappe.get_doc({
                "doctype": "Employee",
                "name": "HR-EMP-EXT-01",
                "employee": "HR-EMP-EXT-01",
                "first_name": "Extension Test",
                "status": "Active",
                "relieving_date": "2026-05-01"
            })
            emp.flags.ignore_mandatory = True
            emp.insert(ignore_permissions=True)

        # Create parent Resignation
        self.resignation = frappe.get_doc({
            "doctype": "Employee Resignation",
            "employee_id": "HR-EMP-EXT-01",
            "relieving_date": "2026-05-01",
            "employees": [{
                "employee": "HR-EMP-EXT-01",
                "employee_name": "Extension Test",
            }]
        })
        self.resignation.flags.ignore_mandatory = True
        self.resignation.insert(ignore_permissions=True)

        # Create linked PMR
        self.pmr = frappe.get_doc({
            "doctype": "Project Manpower Request",
            "employee_resignation": self.resignation.name,
            "deployment_date": "2026-04-20", # Assumes 11 days OJT
            "ojt_days": 11,
            "title": "Test PMR"
        })
        self.pmr.flags.ignore_mandatory = True
        self.pmr.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_missing_extended_date_blocks_approval(self):
        ext = frappe.get_doc({
            "doctype": "Employee Resignation Extension",
            "employee_resignation": self.resignation.name,
            "workflow_state": "Pending"
        })
        ext.flags.ignore_mandatory = True
        ext.insert(ignore_permissions=True)
        
        # Transition to Approved without date
        ext.workflow_state = "Approved"
        with self.assertRaises(frappe.ValidationError):
            ext.save(ignore_permissions=True)

    def test_extension_approval_side_effects(self):
        ext = frappe.get_doc({
            "doctype": "Employee Resignation Extension",
            "employee_resignation": self.resignation.name,
            "workflow_state": "Pending",
            "extended_relieving_date": "2026-05-15"
        })
        ext.flags.ignore_mandatory = True
        ext.insert(ignore_permissions=True)
        
        # Approve extension
        ext.workflow_state = "Approved"
        ext.save(ignore_permissions=True)
        
        # 1. Assert Parent Resignation Updated
        res_date = frappe.db.get_value("Employee Resignation", self.resignation.name, "relieving_date")
        self.assertEqual(getdate(res_date), getdate("2026-05-15"))
        
        # 2. Assert Employee Record Updated
        emp_date = frappe.db.get_value("Employee", "HR-EMP-EXT-01", "relieving_date")
        self.assertEqual(getdate(emp_date), getdate("2026-05-15"))
        
        # 3. Assert PMR Deployment Date Updated (15th - 11 OJT = 4th)
        pmr_date = frappe.db.get_value("Project Manpower Request", self.pmr.name, "deployment_date")
        self.assertEqual(getdate(pmr_date), getdate("2026-05-04"))
