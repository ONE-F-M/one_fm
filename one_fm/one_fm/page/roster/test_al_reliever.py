# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Assigning an annual-leave reliever writes one marked Basic schedule per covered day."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions import (
	create_annual_leave_reliever_actions,
)
from one_fm.one_fm.page.roster.roster import (
	AnnualLeaveReliefOvertimeError,
	assign_annual_leave_reliever,
	get_al_relief_context,
)

LEAVE = "AL-RELIEF-TEST-LEAVE"
SEED = "AL-RELIEF-TEST-SEED-"


def future_monday(offset):
	start = getdate(add_days(today(), offset))
	return add_days(start, (0 - start.weekday()) % 7)


class TestAssignAnnualLeaveReliever(FrappeTestCase):
	def setUp(self):
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active", "relieving_date": ["is", "not set"], "date_of_joining": ["is", "set"]},
			pluck="name",
			limit=2,
		)
		role = frappe.db.get_value(
			"Operations Role",
			{"shift": ["is", "set"], "site": ["is", "set"], "project": ["is", "set"]},
			["name", "shift", "site", "project"],
			as_dict=True,
		)
		if len(employees) < 2 or not role:
			self.skipTest("needs two active employees and an Operations Role with shift, site and project")
		self.employee, self.reliever = employees
		self.role = role
		frappe.db.set_value("Employee", self.employee, {
			"project": role.project,
			"site": role.site,
			"shift": role.shift,
			"custom_operations_role_allocation": role.name,
		})
		# No day-off or weekend reliever role: annual leave relief must not require one.
		frappe.db.set_value("Employee", self.reliever, {
			"shift_working": 1,
			"custom_is_reliever": 0,
			"custom_is_weekend_reliever": 0,
		})

		# Monday to Saturday, so a Friday and a Saturday are covered too
		self.from_date = future_monday(900)
		self.to_date = add_days(self.from_date, 5)
		if frappe.db.exists("Employee Schedule", {
			"employee": self.reliever, "date": ["between", [self.from_date, self.to_date]],
		}):
			self.skipTest("the reliever is already rostered in the test range")
		self.leave = self._leave(LEAVE, self.employee)

	def tearDown(self):
		frappe.db.delete("Employee Schedule", {"employee": self.reliever, "date": ["between", [self.from_date, self.to_date]]})
		frappe.db.delete("Employee Schedule", {"name": ["like", SEED + "%"]})
		frappe.db.delete("Leave Application", {"name": ["like", LEAVE + "%"]})
		frappe.db.delete("Roster Employee Actions", {"employee": self.reliever, "start_date": self.from_date})

	def _leave(self, name, employee):
		frappe.get_doc({
			"doctype": "Leave Application",
			"name": name,
			"employee": employee,
			"leave_type": "Annual Leave",
			"from_date": self.from_date,
			"to_date": self.to_date,
			"status": "Approved",
			"docstatus": 1,
		}).db_insert()
		return name

	def _seed(self, suffix, roster_type="Basic", **values):
		frappe.get_doc({
			"doctype": "Employee Schedule",
			"name": SEED + suffix,
			"employee": self.reliever,
			"date": self.from_date,
			"roster_type": roster_type,
			"employee_availability": "Working",
			**values,
		}).db_insert()
		return SEED + suffix

	def _assign(self, **kwargs):
		return assign_annual_leave_reliever(
			self.employee, self.leave, str(self.from_date), str(self.to_date), self.reliever, **kwargs
		)

	def _rows(self):
		return frappe.get_all(
			"Employee Schedule",
			filters={"employee": self.reliever, "date": ["between", [self.from_date, self.to_date]], "roster_type": "Basic"},
			fields=["name", "date", "employee_availability", "shift", "operations_role", "is_annual_leave_reliever",
				"leave_application", "is_day_off_reliever", "is_weekend_reliever", "is_relieving_schedule"],
		)

	def test_every_covered_day_gets_the_covered_post(self):
		result = self._assign()

		rows = self._rows()
		self.assertEqual(len(rows), 6)
		self.assertEqual(sorted(result["schedules"]), sorted(row.name for row in rows))
		for row in rows:
			with self.subTest(date=row.date):
				self.assertEqual(row.employee_availability, "Working")
				self.assertEqual(row.shift, self.role.shift)
				self.assertEqual(row.operations_role, self.role.name)
				self.assertEqual(row.is_annual_leave_reliever, 1)
				self.assertEqual(row.leave_application, self.leave)

	def test_only_the_annual_leave_flag_is_set(self):
		self._seed("FLAGGED", is_day_off_reliever=1, is_relieving_schedule=1, relieving_employee_schedule="X")

		self._assign()

		for row in self._rows():
			with self.subTest(date=row.date):
				self.assertEqual(
					(row.is_annual_leave_reliever, row.is_day_off_reliever, row.is_weekend_reliever, row.is_relieving_schedule),
					(1, 0, 0, 0),
				)

	def test_an_existing_schedule_is_updated_not_duplicated(self):
		existing = self._seed("EXISTING", employee_availability="Day Off")

		self._assign()

		rows = [row for row in self._rows() if row.date == self.from_date]
		self.assertEqual([row.name for row in rows], [existing])
		self.assertEqual(rows[0].employee_availability, "Working")

	def test_a_reliever_without_a_reliever_role_is_accepted(self):
		self.assertFalse(frappe.db.get_value("Employee", self.reliever, "custom_is_reliever"))
		self.assertEqual(len(self._assign()["schedules"]), 6)

	def test_a_leave_of_another_employee_is_refused(self):
		self.leave = self._leave(LEAVE + "-OTHER", self.reliever)

		with self.assertRaisesRegex(frappe.ValidationError, "does not belong"):
			self._assign()

	def test_the_reliever_cannot_be_the_employee_on_leave(self):
		with self.assertRaisesRegex(frappe.ValidationError, "own reliever"):
			assign_annual_leave_reliever(
				self.employee, self.leave, str(self.from_date), str(self.to_date), self.employee
			)

	def test_overtime_blocks_until_cancel_is_confirmed(self):
		overtime = self._seed("OT", roster_type="Over-Time", workflow_state="Active")

		with self.assertRaises(AnnualLeaveReliefOvertimeError):
			self._assign()
		self.assertTrue(frappe.db.exists("Employee Schedule", overtime))
		self.assertEqual(self._rows(), [])

		result = self._assign(cancel_overtime=1)

		self.assertFalse(frappe.db.exists("Employee Schedule", overtime))
		self.assertEqual(result["deleted_overtime"], [overtime])

	def test_rejected_overtime_does_not_block(self):
		self._seed("OT", roster_type="Over-Time", workflow_state="Rejected")

		self.assertEqual(self._assign()["deleted_overtime"], [])

	def test_a_user_without_a_roster_role_is_refused(self):
		with self.set_user("Guest"):
			with self.assertRaises(frappe.PermissionError):
				self._assign()
			with self.assertRaises(frappe.PermissionError):
				get_al_relief_context(self.employee, str(self.from_date), str(self.to_date))

	def test_context_finds_the_leave_and_the_post(self):
		context = get_al_relief_context(self.employee, str(self.from_date), str(self.to_date))

		self.assertEqual(context["leave_application"], self.leave)
		self.assertEqual(context["shift"], self.role.shift)
		self.assertEqual(context["operations_role"], self.role.name)

	def test_cancelling_the_leave_flags_the_reliever_for_action(self):
		self._assign()

		create_annual_leave_reliever_actions(self.leave)

		action = frappe.db.get_value(
			"Roster Employee Actions",
			{"employee": self.reliever, "start_date": self.from_date},
			["end_date", "status", "missing_dates"],
			as_dict=True,
		)
		self.assertIsNotNone(action)
		self.assertEqual(action.end_date, self.to_date)
		self.assertEqual(action.status, "Pending")
		self.assertEqual(action.missing_dates.split(", ")[0], str(self.from_date))
		self.assertEqual(len(action.missing_dates.split(", ")), 6)
