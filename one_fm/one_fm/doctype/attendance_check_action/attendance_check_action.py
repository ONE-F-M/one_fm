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

	def validate(self):
		self.populate_from_attendance_check()
		self.set_grace_and_deadline()

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
