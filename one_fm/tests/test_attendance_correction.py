# Tests for the Payroll Operator "Attendance Correction" feature.
import random
import string

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_first_day, get_last_day, getdate, today

from one_fm.overrides.attendance import (
	apply_attendance_correction,
	is_within_correction_window,
)


class TestAttendanceCorrectionWindow(FrappeTestCase):
	"""Deterministic checks for the correction deadline helper."""

	def test_within_current_month(self):
		# An attendance dated this month is always inside the window.
		self.assertTrue(is_within_correction_window(today()))

	def test_last_day_of_next_month_is_inclusive(self):
		# attendance month + 1 month, last day => still allowed today only if that day >= today.
		# Use an attendance date in the previous month so the deadline is this month's context.
		attendance_date = get_first_day(add_months(getdate(today()), -1))
		deadline = get_last_day(add_months(getdate(attendance_date), 1))
		expected = getdate(today()) <= getdate(deadline)
		self.assertEqual(is_within_correction_window(attendance_date), expected)

	def test_old_attendance_is_closed(self):
		# Two months ago => window closed.
		old_date = get_first_day(add_months(getdate(today()), -3))
		self.assertFalse(is_within_correction_window(old_date))

	def test_empty_date(self):
		self.assertFalse(is_within_correction_window(None))


class TestApplyAttendanceCorrection(FrappeTestCase):
	"""Guard and behaviour checks for the whitelisted correction method."""

	def setUp(self):
		suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

		# Minimal employee (SQL insert to skip heavy controller validation).
		self.employee = f"TEST-EMP-{suffix}"
		frappe.db.sql("DELETE FROM `tabEmployee` WHERE name=%s", (self.employee,))
		frappe.db.sql(
			"""INSERT INTO `tabEmployee` (name, employee_name, first_name, status)
			VALUES (%s, %s, %s, %s)""",
			(self.employee, f"Test Emp {suffix}", "Test", "Active"),
		)

		# Submitted, Basic-roster Shift Assignment for the same employee/date.
		self.shift_assignment = f"TEST-SA-{suffix}"
		frappe.db.sql("DELETE FROM `tabShift Assignment` WHERE name=%s", (self.shift_assignment,))
		frappe.db.sql(
			"""INSERT INTO `tabShift Assignment`
			(name, employee, start_date, roster_type, custom_day_off_ot, status, docstatus)
			VALUES (%s, %s, %s, %s, %s, %s, %s)""",
			(self.shift_assignment, self.employee, today(), "Basic", 0, "Active", 1),
		)

		# Employee Schedule for the same employee/date/roster_type.
		self.employee_schedule = f"TEST-ES-{suffix}"
		frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name=%s", (self.employee_schedule,))
		frappe.db.sql(
			"""INSERT INTO `tabEmployee Schedule`
			(name, employee, date, roster_type, day_off_ot, employee_availability)
			VALUES (%s, %s, %s, %s, %s, %s)""",
			(self.employee_schedule, self.employee, today(), "Basic", 0, "Working"),
		)

		# Submitted, Basic-roster Attendance dated today (inside the window), linked
		# to the Shift Assignment above.
		self.attendance = f"TEST-ATT-{suffix}"
		frappe.db.sql("DELETE FROM `tabAttendance` WHERE name=%s", (self.attendance,))
		frappe.db.sql(
			"""INSERT INTO `tabAttendance`
			(name, employee, attendance_date, status, roster_type, day_off_ot, shift_assignment, docstatus)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
			(self.attendance, self.employee, today(), "Present", "Basic", 0, self.shift_assignment, 1),
		)
		frappe.db.commit()
		self.addCleanup(self._cleanup)

		self._ensure_role("Payroll Operator")

	def _cleanup(self):
		frappe.set_user("Administrator")
		for doctype in ("Attendance", "Shift Assignment", "Employee Schedule"):
			frappe.db.sql(
				"DELETE FROM `tabComment` WHERE reference_doctype=%s AND reference_name IN (%s, %s, %s)",
				(doctype, self.attendance, self.shift_assignment, self.employee_schedule),
			)
		frappe.db.sql("DELETE FROM `tabAttendance` WHERE name=%s", (self.attendance,))
		frappe.db.sql("DELETE FROM `tabShift Assignment` WHERE name=%s", (self.shift_assignment,))
		frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name=%s", (self.employee_schedule,))
		frappe.db.sql("DELETE FROM `tabEmployee` WHERE name=%s", (self.employee,))
		frappe.db.commit()

	def _ensure_role(self, role):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

	def test_success_as_payroll_operator(self):
		frappe.set_user("Administrator")  # Administrator holds all roles incl. Payroll Operator
		result = apply_attendance_correction(self.attendance, day_off_ot=1, reason="Correcting Roster Mistake")
		self.assertTrue(result["success"])

		doc = frappe.get_doc("Attendance", self.attendance)
		self.assertEqual(doc.day_off_ot, 1)
		self.assertEqual(doc.custom_correction_reason, "Correcting Roster Mistake")

	def test_cascade_updates_all_three_doctypes(self):
		frappe.set_user("Administrator")
		apply_attendance_correction(self.attendance, day_off_ot=1, reason="Correcting Roster Mistake")

		self.assertEqual(frappe.db.get_value("Attendance", self.attendance, "day_off_ot"), 1)
		self.assertEqual(
			frappe.db.get_value("Shift Assignment", self.shift_assignment, "custom_day_off_ot"), 1
		)
		self.assertEqual(
			frappe.db.get_value("Employee Schedule", self.employee_schedule, "day_off_ot"), 1
		)

	def test_audit_trail_added_on_all_three_doctypes(self):
		frappe.set_user("Administrator")
		reason = "Correcting Roster Mistake"
		apply_attendance_correction(self.attendance, day_off_ot=1, reason=reason)

		targets = {
			"Attendance": self.attendance,
			"Shift Assignment": self.shift_assignment,
			"Employee Schedule": self.employee_schedule,
		}
		for doctype, name in targets.items():
			# AC2: a Comment holding the Reason for Change text.
			comment = frappe.db.exists("Comment", {
				"reference_doctype": doctype,
				"reference_name": name,
				"comment_type": "Comment",
				"content": ["like", f"%{reason}%"],
			})
			self.assertTrue(comment, f"Missing correction Comment on {doctype}")

			# AC3: an Info entry recording the operator's User ID.
			info = frappe.db.exists("Comment", {
				"reference_doctype": doctype,
				"reference_name": name,
				"comment_type": "Info",
				"content": ["like", "%Administrator%"],
			})
			self.assertTrue(info, f"Missing activity-log Info entry on {doctype}")

	def test_reason_is_mandatory(self):
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			apply_attendance_correction(self.attendance, day_off_ot=1, reason="   ")

	def test_already_corrected_is_blocked(self):
		frappe.set_user("Administrator")
		apply_attendance_correction(self.attendance, day_off_ot=1, reason="First fix")
		with self.assertRaises(frappe.ValidationError):
			apply_attendance_correction(self.attendance, day_off_ot=0, reason="Second fix")

	def test_non_basic_roster_is_blocked(self):
		frappe.db.set_value("Attendance", self.attendance, "roster_type", "Over-Time")
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			apply_attendance_correction(self.attendance, day_off_ot=1, reason="Fix")

	def test_out_of_window_is_blocked(self):
		old_date = get_first_day(add_months(getdate(today()), -3))
		frappe.db.set_value("Attendance", self.attendance, "attendance_date", old_date)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			apply_attendance_correction(self.attendance, day_off_ot=1, reason="Fix")

	def test_draft_attendance_is_blocked(self):
		frappe.db.set_value("Attendance", self.attendance, "docstatus", 0)
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			apply_attendance_correction(self.attendance, day_off_ot=1, reason="Fix")
