# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate, nowdate

# Grace period (in days) auto-applied for both purchasing methods.
DEFAULT_GRACE_PERIOD = 14

# Statuses that resolve the action's grace period. Once the status is any of
# these, the employee's attendance checks revert to normal manual generation
# (no more auto-fill from the source check). "Draft" is the only active state.
GRACE_ENDING_STATUSES = ("Purchased", "Closed", "Deadline Breached")


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
		self.validate_deadline_breached_status()

	def validate_deadline_breached_status(self):
		"""Guard the manual "Deadline Breached" transition.

		Per the acceptance criteria a breach is only valid once the current date
		*strictly* exceeds the Deadline Date (i.e. the whole deadline day, end of
		day, has elapsed). The status is set manually by the assigned user — this
		simply prevents flagging a breach while the employee is still within the
		grace window.
		"""
		if self.status != "Deadline Breached":
			return

		if not self.deadline_date or getdate(nowdate()) <= getdate(self.deadline_date):
			frappe.throw(
				_("Status can only be set to 'Deadline Breached' after the Deadline Date ({0}) has passed.").format(
					frappe.format(self.deadline_date, {"fieldtype": "Date"}) if self.deadline_date else _("not set")
				)
			)

	def validate_no_open_action(self):
		"""Block creating a new Attendance Check Action when the employee already
		has one that is still blocking.

		A record keeps blocking a new lifecycle until its Deadline Date has passed
		or it has been Closed (see ``get_open_action_for_employee``). This prevents
		duplicate overlapping actions inside the same grace window while still
		letting a new issue raised after the deadline start its own action.
		"""
		if not self.employee:
			return

		open_action = get_open_action_for_employee(self.employee, exclude=self.name)
		if open_action:
			frappe.throw(
				_("An active Attendance Check Action ({0}) already exists for {1}. Close it, or wait for its Deadline Date to pass, before creating a new one.").format(
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

	def before_update_after_submit(self):
		# The Deadline Date is editable after submission (allow_on_submit) so an
		# operator can grant an extension on a locked record. Recompute the Grace
		# Period from the new Deadline Date so the two stay consistent — validate()
		# does not run on after-submit updates, so this must be done explicitly.
		self.set_grace_and_deadline()

	def on_submit(self):
		# "Closed" is the submitted state.
		self.db_set("status", "Closed")


def get_open_action_for_employee(employee, exclude=None, on_date=None):
	"""Return the name of an Attendance Check Action that still blocks creating a
	new one for the employee, or None.

	An action keeps blocking a fresh lifecycle until either its Deadline Date has
	*passed* (the current date is strictly after the deadline) or it has been
	Closed. This lets a genuinely new issue raised after the deadline start its
	own action, while preventing duplicate overlapping actions inside the same
	grace window. An action with no Deadline Date set is treated as not-yet-passed
	and therefore keeps blocking.

	Args:
		employee (str): Employee to check.
		exclude (str, optional): Attendance Check Action name to exclude (self).
		on_date (str | date, optional): Date to test the deadline against
			(defaults to today).
	"""
	if not employee:
		return None

	on_date = getdate(on_date) if on_date else getdate(nowdate())

	filters = {
		"employee": employee,
		"status": ["!=", "Closed"],
		"docstatus": ["<", 2],
	}
	if exclude:
		filters["name"] = ["!=", exclude]

	candidates = frappe.get_all(
		"Attendance Check Action",
		filters=filters,
		fields=["name", "deadline_date"],
	)
	for candidate in candidates:
		if not candidate.deadline_date or getdate(candidate.deadline_date) >= on_date:
			return candidate.name

	return None


def get_active_grace_action(employee, on_date):
	"""Return the open Attendance Check Action whose grace window covers ``on_date``.

	The grace period is active only while the action is still in "Draft" (and not
	cancelled) and ``on_date`` falls within the inclusive window
	``start_date <= on_date <= deadline_date``. Once the assigned user moves the
	status to Purchased, Closed or Deadline Breached, the grace period ends and
	the employee's attendance checks revert to normal manual generation.

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
			"status": "Draft",
			"docstatus": ["<", 2],
			"start_date": ["<=", on_date],
			"deadline_date": [">=", on_date],
		},
		["name", "attendance_check"],
		as_dict=True,
	)
