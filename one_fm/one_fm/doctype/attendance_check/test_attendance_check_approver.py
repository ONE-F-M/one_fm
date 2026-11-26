# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-004923: Attendance Check approver is resolved from the Operations Site on the
Shift Assignment for the check date, with fallbacks to the Employee's default site.

These tests run against existing site data: two Active Operations Sites and three
Active Employees with a user_id are picked in setUpClass and linked together with
frappe.db.set_value. Everything is rolled back by FrappeTestCase.
"""
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.utils import has_super_user_role

APPROVER_LOG_TITLE = "Attendance Check Approver"
TEST_DATE = "2031-03-15"


class TestAttendanceCheckApprover(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        sites = frappe.get_all("Operations Site", filters={"status": "Active"}, pluck="name", limit=2)
        if len(sites) < 2:
            raise unittest.SkipTest("Need two Active Operations Sites")
        cls.site_a, cls.site_b = sites

        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active", "user_id": ["is", "set"]},
            fields=["name", "user_id"],
            limit=60,
        )
        picked, seen_users = [], set()
        for row in employees:
            if row.user_id in seen_users or has_super_user_role(row.user_id):
                continue
            seen_users.add(row.user_id)
            picked.append(row)
            if len(picked) == 3:
                break
        if len(picked) < 3:
            raise unittest.SkipTest("Need three Active Employees with distinct non-super-user users")

        cls.employee, cls.sup_a, cls.sup_b = [p.name for p in picked]
        cls.user_a = picked[1].user_id
        cls.user_b = picked[2].user_id

    def setUp(self):
        # employee: default site A, no reports_to. Site A -> sup_a, site B -> sup_b.
        for field, value in (("reports_to", None), ("site", self.site_a)):
            frappe.db.set_value("Employee", self.employee, field, value, update_modified=False)
        frappe.db.set_value("Operations Site", self.site_a, "site_supervisor", self.sup_a, update_modified=False)
        frappe.db.set_value("Operations Site", self.site_b, "site_supervisor", self.sup_b, update_modified=False)
        frappe.db.set_value("Employee", self.sup_b, "user_id", self.user_b, update_modified=False)
        frappe.db.delete(
            "Error Log", {"method": APPROVER_LOG_TITLE, "error": ["like", f"%{self.employee}%"]}
        )

    def make_check(self, **kwargs):
        check = frappe.new_doc("Attendance Check")
        check.employee = self.employee
        check.date = TEST_DATE
        check.roster_type = "Basic"
        check.update(kwargs)
        return check

    def approver_logs(self):
        return frappe.get_all(
            "Error Log",
            filters={"method": APPROVER_LOG_TITLE, "error": ["like", f"%{self.employee}%"]},
            fields=["name", "error"],
        )

    # AC1
    def test_approver_is_shift_site_supervisor_user(self):
        check = self.make_check()
        approver = check.get_approver_user(self.site_b)
        self.assertEqual(approver, self.user_b)
        self.assertNotEqual(approver, self.user_a)
        self.assertEqual(self.approver_logs(), [])

        check.fetch_and_set_site_supervisor(self.site_b)
        self.assertEqual(check.operations_site, self.site_b)
        self.assertEqual(check.site_supervisor, self.sup_b)

        check.set_attedance_check_approver(self.site_b)
        self.assertEqual(check.approver, self.user_b)

    # AC2
    def test_no_shift_assignment_falls_back_to_employee_site(self):
        check = self.make_check()
        self.assertEqual(check.get_approver_user(None), self.user_a)
        self.assertEqual(self.approver_logs(), [])

    # AC3
    def test_site_without_supervisor_falls_back_and_logs(self):
        frappe.db.set_value("Operations Site", self.site_b, "site_supervisor", None, update_modified=False)
        check = self.make_check()
        self.assertEqual(check.get_approver_user(self.site_b), self.user_a)
        logs = self.approver_logs()
        self.assertEqual(len(logs), 1)
        self.assertIn("has no supervisor", logs[0].error)
        self.assertIn(self.site_b, logs[0].error)

    # AC4
    def test_supervisor_without_user_falls_back_and_logs(self):
        frappe.db.set_value("Employee", self.sup_b, "user_id", None, update_modified=False)
        check = self.make_check()
        self.assertEqual(check.get_approver_user(self.site_b), self.user_a)
        logs = self.approver_logs()
        self.assertEqual(len(logs), 1)
        self.assertIn("has no user account linked", logs[0].error)
        self.assertIn(self.sup_b, logs[0].error)

        # site_supervisor on the check still shows the Shift Assignment site's supervisor
        check.fetch_and_set_site_supervisor(self.site_b)
        self.assertEqual(check.site_supervisor, self.sup_b)
        self.assertEqual(check.operations_site, self.site_b)

    def test_reports_to_wins(self):
        frappe.db.set_value("Employee", self.employee, "reports_to", self.sup_a, update_modified=False)
        check = self.make_check()
        self.assertEqual(check.get_approver_user(self.site_b), self.user_a)
        self.assertEqual(self.approver_logs(), [])

    def test_get_shift_site_uses_assignment_covering_date(self):
        covering = frappe.db.sql(
            """
            SELECT employee, roster_type, end_date
            FROM `tabShift Assignment`
            WHERE docstatus = 1 AND status = 'Active'
                AND end_date > start_date AND ifnull(site, '') != ''
            ORDER BY end_date DESC
            LIMIT 1
            """,
            as_dict=True,
        )
        if not covering:
            self.skipTest("No overnight Active Shift Assignment with a site exists")

        row = covering[0]
        check = self.make_check(employee=row.employee, roster_type=row.roster_type, date=row.end_date)
        expected = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": row.employee,
                "roster_type": row.roster_type,
                "docstatus": 1,
                "status": "Active",
                "start_date": ["<=", row.end_date],
                "end_date": [">=", row.end_date],
            },
            fields=["site"],
            order_by="start_date desc",
            limit=1,
        )[0].site
        self.assertEqual(check.get_shift_site(), expected or None)

    def test_both_supervisors_missing_does_not_raise(self):
        frappe.db.set_value("Operations Site", self.site_a, "site_supervisor", None, update_modified=False)
        frappe.db.set_value("Operations Site", self.site_b, "site_supervisor", None, update_modified=False)
        check = self.make_check()
        try:
            approver = check.get_approver_user(self.site_b)
        except Exception as e:  # pragma: no cover - failure path
            self.fail(f"get_approver_user raised {e!r}")
        self.assertTrue(approver is None or isinstance(approver, str))
        self.assertEqual(len(self.approver_logs()), 1)
