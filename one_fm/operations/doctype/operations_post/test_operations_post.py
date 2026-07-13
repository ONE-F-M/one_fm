# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.tests.utils import create_test_company
from frappe.utils import add_days, nowdate, getdate


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

    def _create_test_location(self):
        location_name = "Test Operations Location"
        if not frappe.db.exists("Location", location_name):
            frappe.get_doc({
                "doctype": "Location",
                "location_name": location_name,
                "latitude": 29.3759,
                "longitude": 47.9774,
                "geofence_radius": 100
            }).insert(ignore_permissions=True)
        return location_name

    def _create_test_site(self):
        site = frappe.get_doc({
            "doctype": "Operations Site",
            "site_name": "Test Operations Site",
            "status": "Active",
            "company": "_Test Company",
            "site_location": self._create_test_location()
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
        
        self.assertIn("Inactive", str(cm.exception))

    def test_post_activation_date_appended(self):
        """Test that making an Active post Inactive appends to operations_post_activation child table"""
        post = self._create_test_operations_post(status="Active", start_date=nowdate(), end_date=add_days(nowdate(), 5))
        
        post.status = "Inactive"
        post.save(ignore_permissions=True)

        self.assertEqual(len(post.operations_post_activation), 1)
        self.assertEqual(getdate(post.operations_post_activation[0].operations_post_start_date), getdate(nowdate()))
        self.assertEqual(getdate(post.operations_post_activation[0].operations_post_end_date), getdate(add_days(nowdate(), 5)))
        self.assertIsNone(post.start_date)
        self.assertIsNone(post.end_date)

    def test_reactivation_archives_previous_dates(self):
        """AC3: editing the main dates while the status stays Active must archive the
        previous window into the history table and keep the new dates on the parent."""
        post = self._create_test_operations_post(
            status="Active", start_date=nowdate(), end_date=add_days(nowdate(), 5)
        )

        # Extend/reactivate to a new range without changing the status.
        post.start_date = add_days(nowdate(), 10)
        post.end_date = add_days(nowdate(), 20)
        post.save(ignore_permissions=True)

        self.assertEqual(len(post.operations_post_activation), 1)
        self.assertEqual(getdate(post.operations_post_activation[0].operations_post_start_date), getdate(nowdate()))
        self.assertEqual(getdate(post.operations_post_activation[0].operations_post_end_date), getdate(add_days(nowdate(), 5)))
        self.assertEqual(getdate(post.start_date), getdate(add_days(nowdate(), 10)))
        self.assertEqual(getdate(post.end_date), getdate(add_days(nowdate(), 20)))

    def test_no_duplicate_activation_row_when_dates_unchanged(self):
        """AC3: saving without modifying the dates must not create a history row."""
        post = self._create_test_operations_post(
            status="Active", start_date=nowdate(), end_date=add_days(nowdate(), 5)
        )

        # Change an unrelated field, leave the dates as-is.
        post.handover = 1
        post.save(ignore_permissions=True)

        self.assertEqual(len(post.operations_post_activation), 0)

    def test_original_start_date_preserved(self):
        """AC5: the first activation date is captured once and never overwritten."""
        post = self._create_test_operations_post(
            status="Active", start_date=nowdate(), end_date=add_days(nowdate(), 5)
        )
        self.assertEqual(getdate(post.original_start_date), getdate(nowdate()))

        # Reactivate/extend to a later range - original must stay put.
        post.start_date = add_days(nowdate(), 10)
        post.save(ignore_permissions=True)
        self.assertEqual(getdate(post.original_start_date), getdate(nowdate()))

    def test_get_active_windows_and_is_date_in_windows(self):
        """AC4: active windows combine the main window with logged history windows."""
        from one_fm.operations.doctype.operations_post.operations_post import (
            get_active_windows, is_date_in_windows,
        )

        post = frappe._dict({
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
            "operations_post_activation": [
                frappe._dict({
                    "operations_post_start_date": "2026-01-01",
                    "operations_post_end_date": "2026-01-15",
                }),
            ],
        })

        windows = get_active_windows(post)
        self.assertEqual(len(windows), 2)
        self.assertTrue(is_date_in_windows("2026-02-10", windows))   # main window
        self.assertTrue(is_date_in_windows("2026-01-10", windows))   # history window
        self.assertFalse(is_date_in_windows("2026-01-20", windows))  # gap between windows
        self.assertFalse(is_date_in_windows("2026-03-05", windows))  # after main window

    def test_get_active_intervals_in_period(self):
        """AC4: windows are clipped to the period and merged so overlaps are counted once."""
        from frappe.utils import getdate
        from one_fm.operations.doctype.post_scheduler_checker.post_scheduler_checker import (
            get_active_intervals_in_period,
        )

        windows = [
            (getdate("2026-02-05"), getdate("2026-02-28")),
            (getdate("2026-01-20"), getdate("2026-02-03")),  # spills before the period
        ]
        intervals = get_active_intervals_in_period(
            windows, getdate("2026-02-01"), getdate("2026-02-28")
        )

        # Feb 1-3 and Feb 5-28 -> two disjoint intervals, 3 + 24 = 27 active days.
        self.assertEqual(len(intervals), 2)
        total_days = sum((end - start).days + 1 for start, end in intervals)
        self.assertEqual(total_days, 27)

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