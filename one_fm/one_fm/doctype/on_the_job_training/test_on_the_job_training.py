# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate, add_days

class TestOntheJobTraining(FrappeTestCase):
    def setUp(self):
        self.employee = self.create_test_employee()
        
        # Create Item for Role
        self.item = self.create_simple_doc("Item", "TEST-OJT-ITEM", {"item_group": "All Item Groups"})
        
        # Create Contact for Site
        self.contact = self.create_simple_doc("Contact", "TEST-OJT-CONTACT", {"first_name": "Test", "last_name": "Contact"})

        self.project = self.create_simple_doc("Project", "TEST-OJT-PROJECT", {"project_name": "Test Project"})
        
        self.site = self.create_simple_doc("Operations Site", "TEST-OJT-SITE", {
            "site_name": "Test Site",
            "poc": [{"poc": self.contact}]
        })
        
        self.shift = self.create_simple_doc("Operations Shift", "TEST-OJT-SHIFT", {
            "site": self.site,
            "project": self.project,
            "start_time": "08:00:00",
            "end_time": "16:00:00"
        })

        self.role = self.create_simple_doc("Operations Role", "TEST-OJT-ROLE", {
            "post_name": "Test Role",
            "post_abbrv": "TR",
            "sale_item": self.item,
            "shift": self.shift,
            "site": self.site,
            "project": self.project
        })

    def create_test_employee(self):
        if frappe.db.exists("Employee", "TEST-OJT-EMP"):
            return "TEST-OJT-EMP"
            
        # Ensure Department exists
        if not frappe.db.exists("Department", "Test Department - ONE FM"):
            try:
                frappe.get_doc({
                    "doctype": "Department",
                    "department_name": "Test Department",
                    "department_code": "TEST-DEPT",
                    "company": frappe.db.get_single_value("Global Defaults", "default_company") or "ONE FM" 
                }).insert(ignore_permissions=True)
            except frappe.DuplicateEntryError:
                pass
        
        doc = frappe.new_doc("Employee")
        doc.employee = "TEST-OJT-EMP"
        doc.first_name = "Test"
        doc.last_name = "OJT Employee"
        doc.gender = "Male"
        doc.date_of_birth = "1990-01-01"
        doc.date_of_joining = nowdate()
        doc.status = "Active"
        
        # Mandatory fields
        doc.one_fm_first_name_in_arabic = "Test"
        doc.one_fm_last_name_in_arabic = "Employee"
        doc.department = "Test Department - ONE FM" # Use the full name if possible, or link by name
        doc.one_fm_basic_salary = 1000
        
        doc.insert(ignore_permissions=True)
        return doc.name

    def create_simple_doc(self, doctype, name, fields=None):
        if frappe.db.exists(doctype, name):
            return name
        doc = frappe.new_doc(doctype)
        
        # Force name for these doctypes if possible
        if doctype in ["Operations Role", "Operations Shift", "Operations Site", "Project"]:
             doc.name = name
        
        if fields:
            doc.update(fields)
        
        try:
            doc.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
        except frappe.NameError:
            pass 
        except Exception:
            # If creation failed, we might not have a valid name if it relied on autogeneration
            pass
            
        return doc.name
