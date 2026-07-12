# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate

# Grace period (in days) auto-applied for both purchasing methods.
DEFAULT_GRACE_PERIOD = 14


class AttendanceCheckAction(Document):
	def before_naming(self):
		# Populate the naming inputs (employee, start_date) from the source
		# Attendance Check before the name is generated, so the
		# "HR-ACA-{employee}_{start_date}" expression always resolves.
		self.populate_from_attendance_check()

	def before_insert(self):
		# Guard against duplicate lifecycles: a new action can only be created
		# once the employee's previous one has been Closed.
		self.populate_from_attendance_check()
		self.validate_no_open_action()

	def validate(self):
		self.populate_from_attendance_check()
		self.set_grace_and_deadline()

	def validate_no_open_action(self):
		"""Block creating a new Attendance Check Action when the employee already
		has an open (not Closed) one.

		A record is considered "open" while its status is not "Closed" and it has
		not been cancelled. Only once the previous action is Closed may a brand
		new one be started for the same employee.
		"""
		if not self.employee:
			return

		open_action = get_open_action_for_employee(self.employee, exclude=self.name)
		if open_action:
			frappe.throw(
				_("An open Attendance Check Action ({0}) already exists for {1}. Close it before creating a new one.").format(
					open_action, self.employee_name or self.employee
				)
			)

	def populate_from_attendance_check(self):
		"""Fetch Employee, Action and Start Date (= Attendance Check Date) from the source issue."""
		if not self.attendance_check:
			return

		source = frappe.db.get_value(
			"Attendance Check",
			self.attendance_check,
			["employee", "date", "action"],
			as_dict=True,
		)
		if not source:
			return

		if not self.employee:
			self.employee = source.employee
		if not self.start_date:
			self.start_date = source.date
		if not self.action:
			self.action = source.action

	def set_grace_and_deadline(self):
		"""Keep Grace Period and Deadline Date mathematically consistent.

		- Selecting a Purchasing Method defaults the Grace Period to 14 days.
		- Deadline Date is treated as the source of truth when set: Grace Period
		  is derived from it (Deadline Date - Start Date).
		- Otherwise the Deadline Date is derived from Start Date + Grace Period.
		"""
		# Auto-set 14-day grace for Self Purchase / Company Loan when not already set.
		if self.purchasing_method and not self.grace_period:
			self.grace_period = DEFAULT_GRACE_PERIOD

		if self.start_date:
			if self.deadline_date:
				self.grace_period = date_diff(self.deadline_date, self.start_date)
			elif self.grace_period:
				self.deadline_date = add_days(self.start_date, self.grace_period)

		if self.grace_period and self.grace_period < 0:
			frappe.throw(_("Grace Period cannot be negative. Deadline Date must be on or after the Start Date."))

	def on_submit(self):
		# "Closed" is the submitted state.
		self.db_set("status", "Closed")


def get_open_action_for_employee(employee, exclude=None):
	"""Return the name of an open (not Closed, not Cancelled) Attendance Check
	Action for the employee, or None.

	Args:
		employee (str): Employee to check.
		exclude (str, optional): Attendance Check Action name to exclude (self).
	"""
	if not employee:
		return None

	filters = {
		"employee": employee,
		"status": ["!=", "Closed"],
		"docstatus": ["<", 2],
	}
	if exclude:
		filters["name"] = ["!=", exclude]

	return frappe.db.get_value("Attendance Check Action", filters, "name")


def get_active_grace_action(employee, on_date):
	"""Return the open Attendance Check Action whose grace window covers ``on_date``.

	The grace period is active while the action is NOT Closed (and not
	cancelled) and ``on_date`` falls within the inclusive window
	``start_date <= on_date <= deadline_date``.

	Args:
		employee (str): Employee to check.
		on_date (str | date): The date to test against the grace window
			(the Attendance Check's ``date``).

	Returns:
		frappe._dict | None: ``{"name", "attendance_check"}`` of the active
		action, or ``None`` when no grace period is active.
	"""
	if not employee or not on_date:
		return None

	on_date = getdate(on_date)

	return frappe.db.get_value(
		"Attendance Check Action",
		{
			"employee": employee,
			"status": ["!=", "Closed"],
			"docstatus": ["<", 2],
			"start_date": ["<=", on_date],
			"deadline_date": [">=", on_date],
		},
		["name", "attendance_check"],
		as_dict=True,
	)
