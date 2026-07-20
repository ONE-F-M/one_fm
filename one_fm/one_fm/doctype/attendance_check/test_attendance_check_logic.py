
import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.attendance_check.attendance_check import get_grace_period_prefill
from one_fm.one_fm.doctype.attendance_check_action.attendance_check_action import (
    get_active_grace_action,
)

class TestAttendanceCheckLogic(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Resolve an existing company instead of hardcoding a name, so the suite
        # runs on any site (the default company, or the first one available).
        self.company = frappe.defaults.get_global_default("company") or frappe.db.get_value(
            "Company", {}, "name"
        )
        if not self.company:
            self.skipTest("No Company available to run Attendance Check tests")

        # Create a test employee if not exists
        if not frappe.db.exists("Employee", "TEST-EMP-001"):
            emp = frappe.get_doc({
                "doctype": "Employee",
                "employee_number": "TEST-EMP-001",
                "first_name": "Test",
                "last_name": "Employee",
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01",
                "company": self.company,
                "status": "Active"
            })
            # Site-specific custom fields (Arabic names, department, basic salary)
            # are mandatory on Employee here; skip them — the tests only need an
            # Active employee to attach Attendance Checks to.
            emp.flags.ignore_mandatory = True
            emp.insert(ignore_permissions=True)
            self.employee = emp.name
        else:
            self.employee = "TEST-EMP-001"

    def test_mark_attendance_updates_existing(self):
        # Create an Attendance record
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": self.employee,
            "attendance_date": "2024-01-01",
            "status": "Absent",
            "company": self.company,
            "roster_type": "Basic"
        })
        attendance.insert(ignore_permissions=True)
        attendance.submit()
        
        # Create an Attendance Check record
        ac = frappe.get_doc({
            "doctype": "Attendance Check",
            "employee": self.employee,
            "date": "2024-01-01",
            "attendance_status": "Present",
            "roster_type": "Basic",
            "justification": "Other",
            "other_reason": "Test",
            "workflow_state": "Pending Approval" # Valid non-approved workflow state
        })
        ac.insert(ignore_permissions=True)
        
        # Manually call mark_attendance
        ac.mark_attendance()
        
        # Verify Attendance record is updated
        updated_attendance = frappe.get_doc("Attendance", attendance.name)
        self.assertEqual(updated_attendance.status, "Present")
        self.assertEqual(updated_attendance.reference_docname, ac.name)
        self.assertEqual(updated_attendance.comment, "Updated from Attendance Check")

    # ------------------------------------------------------------------
    # Grace-period auto-population (Attendance Check Action)
    # ------------------------------------------------------------------
    def _make_source_check(self, date):
        """Create the original Attendance Check whose justification is carried
        over during the grace period (Out-of-site location -> Issue a New Mobile)."""
        source = frappe.get_doc({
            "doctype": "Attendance Check",
            "employee": self.employee,
            "date": date,
            "attendance_status": "Present",
            "roster_type": "Basic",
            "justification": "Out-of-site location",
            "is_the_employee_physically_onsite": "Yes",
            "screenshot": "/files/original-evidence.png",
        })
        source.insert(ignore_permissions=True)
        return source

    def _make_action(self, source_check, start_date, deadline_date, status="Draft"):
        """Create an Attendance Check Action linked to the source check."""
        action = frappe.get_doc({
            "doctype": "Attendance Check Action",
            "attendance_check": source_check.name,
            "employee": self.employee,
            "action": "Issue a New Mobile",
            "start_date": start_date,
            "deadline_date": deadline_date,
            "status": status,
        })
        action.insert(ignore_permissions=True)
        return action

    def test_source_check_derives_issue_new_mobile(self):
        # Guards the fixture: Out-of-site + physically onsite -> Issue a New Mobile.
        source = self._make_source_check("2026-02-01")
        self.assertEqual(source.action, "Issue a New Mobile")

    def test_get_active_grace_action_within_window(self):
        source = self._make_source_check("2026-02-01")
        self._make_action(source, "2026-02-01", "2026-02-15")

        # A check dated inside the window resolves the active action.
        active = get_active_grace_action(self.employee, "2026-02-05")
        self.assertIsNotNone(active)
        self.assertEqual(active.attendance_check, source.name)

    def test_get_active_grace_action_outside_window(self):
        source = self._make_source_check("2026-02-01")
        self._make_action(source, "2026-02-01", "2026-02-15")

        # A check dated after the deadline has no active grace period.
        self.assertIsNone(get_active_grace_action(self.employee, "2026-02-20"))

    def test_closed_action_is_not_active(self):
        source = self._make_source_check("2026-02-01")
        self._make_action(source, "2026-02-01", "2026-02-15", status="Closed")

        self.assertIsNone(get_active_grace_action(self.employee, "2026-02-05"))

    def test_purchased_action_is_not_active(self):
        # AC2: once the employee has Purchased a mobile the grace period ends and
        # future checks revert to normal manual generation (no more auto-fill).
        source = self._make_source_check("2026-02-01")
        self._make_action(source, "2026-02-01", "2026-02-15", status="Purchased")

        self.assertIsNone(get_active_grace_action(self.employee, "2026-02-05"))

    def test_deadline_breached_action_is_not_active(self):
        # AC3: a Deadline Breached action also ends the grace period. The deadline
        # is in the past so the manual "Deadline Breached" guard is satisfied.
        source = self._make_source_check("2020-02-01")
        self._make_action(source, "2020-02-01", "2020-02-15", status="Deadline Breached")

        self.assertIsNone(get_active_grace_action(self.employee, "2020-02-05"))

    def test_autofill_populates_new_check_during_grace(self):
        source = self._make_source_check("2026-02-01")
        self._make_action(source, "2026-02-01", "2026-02-15")

        # New check inside the window, Present, no justification and no fresh
        # screenshot -> auto-filled from the source and saved without error.
        new_check = frappe.get_doc({
            "doctype": "Attendance Check",
            "employee": self.employee,
            "date": "2026-02-05",
            "attendance_status": "Present",
            "roster_type": "Basic",
        })
        new_check.insert(ignore_permissions=True)

        self.assertEqual(new_check.justification, "Out-of-site location")
        self.assertEqual(new_check.is_the_employee_physically_onsite, "Yes")
        self.assertEqual(new_check.action, "Issue a New Mobile")
        # The original screenshot is NOT carried over; the requirement is bypassed.
        self.assertFalse(new_check.screenshot)

    def test_prefill_helper_returns_payload(self):
        source = self._make_source_check("2026-02-01")
        action = self._make_action(source, "2026-02-01", "2026-02-15")

        data = get_grace_period_prefill(self.employee, "2026-02-05")
        self.assertEqual(data.get("justification"), "Out-of-site location")
        self.assertEqual(data.get("action"), "Issue a New Mobile")
        self.assertEqual(data.get("grace_action"), action.name)

    def test_prefill_helper_empty_outside_grace(self):
        source = self._make_source_check("2026-02-01")
        self._make_action(source, "2026-02-01", "2026-02-15")

        self.assertEqual(get_grace_period_prefill(self.employee, "2026-02-20"), {})

    def test_screenshot_required_without_grace(self):
        # No Attendance Check Action -> the standard screenshot requirement stands.
        check = frappe.get_doc({
            "doctype": "Attendance Check",
            "employee": self.employee,
            "date": "2026-03-01",
            "attendance_status": "Present",
            "roster_type": "Basic",
            "justification": "Out-of-site location",
            "is_the_employee_physically_onsite": "Yes",
        })
        with self.assertRaises(frappe.ValidationError):
            check.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()
