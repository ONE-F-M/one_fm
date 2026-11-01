# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-004231: a Shift Request is not an absence excuse.

fetch_employees_not_in_checkin builds the check-in / late check-in / check-out reminder
list. It used to subtract every employee holding a Shift Request, so those employees never
got a reminder. A Shift Request only moves the employee to a different shift or site; they
must still be reminded. Leave Application and Shift Permission are real excuses and must
still suppress the reminder.

The fixtures are inserted straight into their tables (db_insert), carrying only the columns
the reminder query reads, so the tests do not depend on any data already on the site.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, getdate, now_datetime, today

from one_fm.api.tasks import fetch_employees_not_in_checkin


class TestCheckinReminderShiftRequest(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._created = []  # (doctype, name) rows to remove in tearDown
		self.suffix = frappe.generate_hash(length=8)

		self.employee = self._insert_row(
			"Employee",
			employee_name="WI004231 Reminder Test",
			first_name="WI004231",
			status="Active",
		)
		shift_type = self._insert_row(
			"Shift Type",
			start_time="08:00:00",
			end_time="17:00:00",
			notification_reminder_after_shift_start=10,
			notification_reminder_after_shift_end=10,
			late_entry_grace_period=15,
			supervisor_reminder_shift_start=20,
			supervisor_reminder_start_ends=20,
		)
		site = self._insert_row("Operations Site")
		shift = self._insert_row("Operations Shift", site=site, shift_type=shift_type)
		self.assignment = self._insert_row(
			"Shift Assignment",
			employee=self.employee,
			shift=shift,
			site=site,
			shift_type=shift_type,
			status="Active",
			docstatus=1,
			start_date=today(),
			# Shift start inside the reminder job's look-back window (the past hour).
			start_datetime=add_to_date(now_datetime(), minutes=-5),
			end_datetime=add_to_date(now_datetime(), hours=8),
		)

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

	def _insert_row(self, doctype, **values):
		"""Insert a row straight into the table and return its name."""
		name = f"TEST-WI004231-{self.suffix}-{len(self._created)}"
		now = now_datetime()
		frappe.get_doc({
			"doctype": doctype,
			"name": name,
			"creation": now,
			"modified": now,
			"owner": "Administrator",
			"modified_by": "Administrator",
			**values,
		}).db_insert()
		self._created.append((doctype, name))
		return name

	def _in_reminder_employees(self):
		results = fetch_employees_not_in_checkin() or []
		return [r.get("employee") for r in results if r.get("log_type") == "IN"]

	def test_shift_request_does_not_suppress_reminder(self):
		self._insert_row(
			"Shift Request",
			employee=self.employee,
			docstatus=1,
			from_date=today(),
			to_date=today(),
			workflow_state="Approved",
		)

		self.assertIn(self.employee, self._in_reminder_employees())

	def test_leave_application_still_suppresses_reminder(self):
		self._insert_row(
			"Leave Application",
			employee=self.employee,
			docstatus=1,
			status="Approved",
			from_date=today(),
			to_date=today(),
		)

		self.assertNotIn(self.employee, self._in_reminder_employees())

	def test_arrive_late_shift_permission_still_suppresses_reminder(self):
		self._insert_row(
			"Shift Permission",
			employee=self.employee,
			docstatus=1,
			date=getdate(today()),
			log_type="IN",
			permission_type="Arrive Late",
			workflow_state="Approved",
		)

		self.assertNotIn(self.employee, self._in_reminder_employees())
