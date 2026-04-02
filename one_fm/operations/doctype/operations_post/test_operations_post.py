# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.tests.utils import create_test_company
from frappe.utils import add_days, nowdate


class TestOperationsPost(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        create_test_company()
        
        # Clean up existing test data
        frappe.db.delete("Operations Post", {"post_name": "Test Post"})
        frappe.db.delete("Operations Role", {"post_name": "Test Operations Role"})
        frappe.db.delete("Item", {"item_code": "Test Sale Item"})
        frappe.db.delete("Operations Shift", {"name": "Test Operations Shift"})
        frappe.db.delete("Operations Site", {"site_name": "Test Operations Site"})
        frappe.db.delete("Project", {"project_name": "Test Project"})
        frappe.db.delete("Post Schedule", {"post": ["like", "Test Post%"]})

        self.site = self._create_test_site()
        self.shift = self._create_test_shift()
        self.sale_item = self._create_test_item()
        self.operations_role = self._create_test_operations_role()
        self.project = self._create_test_project()
        self.contract = self._create_test_contract()
        
    def tearDown(self):
        frappe.db.delete("Operations Post", {"post_name": "Test Post"})
        frappe.db.delete("Operations Role", {"post_name": "Test Operations Role"})
        frappe.db.delete("Item", {"item_code": "Test Sale Item"})
        frappe.db.delete("Operations Shift", {"name": "Test Operations Shift"})
        frappe.db.delete("Operations Site", {"site_name": "Test Operations Site"})
        frappe.db.delete("Project", {"project_name": "Test Project"})
        frappe.db.delete("Post Schedule", {"post": ["like", "Test Post%"]})
        frappe.db.delete("Contracts", {"project": "Test Project"})
        
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _create_test_site(self):
        site = frappe.get_doc({
            "doctype": "Operations Site",
            "site_name": "Test Operations Site",
            "status": "Active",
            "company": "_Test Company"
        })
        test_poc_contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": "Test POC",
            "email_id": "test_email@abc.com",
            "phone": "1234567890"
        })
        test_poc_contact.insert(ignore_permissions=True)
        site.append("poc", {
            "poc": test_poc_contact.name
        })
        site.insert(ignore_permissions=True)
        return site

    def _create_test_shift(self):
        test_service_type_name = "Test Service Type"
        if not frappe.db.exists("Service Type", test_service_type_name):
            test_service_type = frappe.get_doc({
                "doctype": "Service Type",
                "service_type": test_service_type_name
            })
            test_service_type.insert(ignore_permissions=True)

        shift = frappe.get_doc({
            "doctype": "Operations Shift",
            "shift_number": 123,
            "site": self.site.name,
            "service_type": test_service_type_name,
            "start_time": "08:00:00",
            "end_time": "16:00:00"
        })
        shift.insert(ignore_permissions=True)
        return shift

    def _create_test_item(self):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "Test Sale Item",
            "item_name": "Test Sale Item",
            "item_group": "All Item Groups",
            "is_stock_item": 0
        })
        item.flags.ignore_mandatory = True
        item.insert(ignore_permissions=True)
        return item

    def _create_test_operations_role(self):
        role = frappe.get_doc({
            "doctype": "Operations Role",
            "post_name": "Test Operations Role",
            "status": "Active",
            "sale_item": self.sale_item.name,
            "shift": self.shift.name,
            "post_abbrv": "Test Post Abbrv"
        })
        role.insert(ignore_permissions=True)
        return role
        
    def _create_test_project(self):
        project = frappe.get_doc({
            "doctype": "Project",
            "project_name": "Test Project",
            "status": "Open",
            "company": "_Test Company",
            "expected_start_date": add_days(nowdate(), -10),
            "expected_end_date": add_days(nowdate(), 10)
        })
        project.insert(ignore_permissions=True)
        return project

    def _create_test_operations_post(self, status="Inactive", **kwargs):
        defaults = {
            "doctype": "Operations Post",
            "post_name": "Test Post",
            "gender": "Male",
            "site_shift": self.shift.name,
            "site": self.site.name,
            "post_template": self.operations_role.name,
            "project": self.project.name,
            "status": status,
        }
        defaults.update(kwargs)
        post = frappe.get_doc(defaults)
        post.insert(ignore_permissions=True)
        return post

    def test_validation_empty_fields(self):
        """Test that validation fails when mandatory fields are missing"""
        post = frappe.get_doc({"doctype": "Operations Post", "gender": "Male", "site_shift": self.shift.name, "status": "Inactive"})
        with self.assertRaises(frappe.exceptions.ValidationError) as cm:
            post.insert(ignore_permissions=True)
        self.assertIn("Post Name cannot be empty", str(cm.exception))

        post_no_gender = frappe.get_doc({"doctype": "Operations Post", "post_name": "Test Post", "site_shift": self.shift.name, "status": "Inactive"})
        self.assertRaises(frappe.ValidationError, post_no_gender.insert)

        post_no_shift = frappe.get_doc({"doctype": "Operations Post", "post_name": "Test Post", "gender": "Male", "status": "Inactive"})
        with self.assertRaises(frappe.exceptions.ValidationError) as cm:
            post_no_shift.insert(ignore_permissions=True)
        self.assertIn("Shift cannot be empty", str(cm.exception))

    def test_operations_role_inactive_validation(self):
        """Test that trying to set post as Active when its role is Inactive fails"""
        self.operations_role.status = "Inactive"
        self.operations_role.save()

        post = self._create_test_operations_post(status="Inactive")
        post.status = "Active"
        post.start_date = nowdate()

        with self.assertRaises(frappe.exceptions.ValidationError) as cm:
            post.save(ignore_permissions=True)
        
        self.assertIn("is Inactive", str(cm.exception))

    def test_post_activation_date_appended(self):
        """Test that making an Active post Inactive appends to operations_post_activation child table"""
        post = self._create_test_operations_post(status="Active", start_date=nowdate(), end_date=add_days(nowdate(), 5))
        
        post.status = "Inactive"
        post.save(ignore_permissions=True)

        self.assertEqual(len(post.operations_post_activation), 1)
        self.assertEqual(post.operations_post_activation[0].operations_post_start_date, nowdate())
        self.assertEqual(post.operations_post_activation[0].operations_post_end_date, add_days(nowdate(), 5))
        self.assertIsNone(post.start_date)
        self.assertIsNone(post.end_date)

    def test_name_validation(self):
        """Test that post forces a specific naming convention"""
        post = self._create_test_operations_post()
        expected_name = f"Test Post-Male|{self.shift.name}"
        self.assertEqual(post.name, expected_name)

    def _create_test_contract(self):
        if frappe.db.exists("Contracts", {"project": self.project.name}):
            return frappe.get_doc("Contracts", {"project": self.project.name})
        contract = frappe.get_doc({
            "doctype": "Contracts",
            "project": self.project.name,
            "start_date": add_days(nowdate(), -5),
            "end_date": add_days(nowdate(), 5),
            "company": "_Test Company",
            "status": "Active"
        })
        contract.append("items", {
            "item_code": self.sale_item.name,
            "quantity": 2,
            "item_type": "Service"
        })
        contract.flags.ignore_mandatory = True
        contract.insert(ignore_permissions=True)
        return contract