# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-004231: a Shift Request is not an absence excuse.

fetch_employees_not_in_checkin builds the check-in / late check-in / check-out reminder
list. It used to subtract every employee holding a submitted Shift Request, so those
employees never got a reminder. A Shift Request only moves the employee to a different
shift or site; they must still be reminded. Leave Application and Shift Permission are real
excuses and must still suppress the reminder.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, getdate, now_datetime, today

from one_fm.api.tasks import fetch_employees_not_in_checkin


def _an_operations_shift():
	name = frappe.db.get_value(
		"Operations Shift",
		{"status": "Active", "shift_type": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active Operations Shift on this site to test against")
	return name


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestCheckinReminderShiftRequest(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = _an_active_employee()
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self._created = []  # (doctype, name) rows to remove in tearDown

		self._clear_employee_rows()
		self._make_shift_assignment()

		# fetch_employees_not_in_checkin returns early outside production, and skips
		# employees on a holiday today; neither is what these tests are about.
		for target, value in (
			("one_fm.api.tasks.production_domain", lambda: True),
			("one_fm.api.tasks.get_holiday_today", lambda *a, **k: {}),
		):
			patcher = patch(target, value)
			patcher.start()
			self.addCleanup(patcher.stop)

	def tearDown(self):
		for doctype, name in reversed(self._created):
			frappe.db.delete(doctype, {"name": name})
		self._clear_employee_rows()

	def _clear_employee_rows(self):
		frappe.db.delete("Shift Assignment", {"employee": self.employee, "start_date": today()})
		frappe.db.delete("Employee Checkin", {"employee": self.employee, "date": today()})

	def _make_shift_assignment(self):
		assignment = frappe.get_doc({
			"doctype": "Shift Assignment",
			"employee": self.employee,
			"company": frappe.defaults.get_user_default("company"),
			"shift": self.shift_name,
			"shift_type": self.shift.shift_type,
			"start_date": today(),
			"status": "Active",
			"roster_type": "Basic",
		})
		assignment.flags.ignore_permissions = True
		assignment.insert(ignore_permissions=True)
		assignment.submit()
		# Put the shift start inside the reminder job's look-back window (the past hour).
		frappe.db.set_value(
			"Shift Assignment",
			assignment.name,
			{
				"start_datetime": add_to_date(now_datetime(), minutes=-5),
				"end_datetime": add_to_date(now_datetime(), hours=8),
				"site": self.shift.site,
			},
			update_modified=False,
		)
		self._created.append(("Shift Assignment", assignment.name))

	def _insert_row(self, doctype, **values):
		"""Insert a row straight into the table; only the columns the reminder query reads matter."""
		name = f"TEST-WI004231-{frappe.generate_hash(length=8)}"
		frappe.get_doc({"doctype": doctype, "name": name, "employee": self.employee, **values}).db_insert()
		self._created.append((doctype, name))

	def _in_reminders(self):
		results = fetch_employees_not_in_checkin() or []
		return [r for r in results if r.get("log_type") == "IN"]

	def test_shift_request_does_not_suppress_reminder(self):
		self._insert_row(
			"Shift Request",
			docstatus=1,
			from_date=today(),
			to_date=today(),
			workflow_state="Approved",
		)

		employees = [r.get("employee") for r in self._in_reminders()]

		self.assertIn(self.employee, employees)

	def test_leave_application_still_suppresses_reminder(self):
		self._insert_row(
			"Leave Application",
			docstatus=1,
			status="Approved",
			from_date=today(),
			to_date=today(),
		)

		employees = [r.get("employee") for r in self._in_reminders()]

		self.assertNotIn(self.employee, employees)

	def test_arrive_late_shift_permission_still_suppresses_reminder(self):
		self._insert_row(
			"Shift Permission",
			docstatus=1,
			date=getdate(today()),
			log_type="IN",
			permission_type="Arrive Late",
			workflow_state="Approved",
		)

		employees = [r.get("employee") for r in self._in_reminders()]

		self.assertNotIn(self.employee, employees)
