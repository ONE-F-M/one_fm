# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
	time_diff_in_hours, getdate, get_first_day, get_last_day,
	flt, rounded
)
from frappe import _
from frappe.query_builder.functions import Sum
from one_fm.api.notification import create_notification_log, get_employee_user_id


class OvertimeRequest(Document):

	def before_insert(self):
		if not self.requested_by:
			self.requested_by = frappe.session.user

	def validate(self):
		self.validate_duplicate()
		self.validate_leave_overlap()
		self.calculate_overtime_hours()
		self.calculate_yearly_overtime_hours()
		self.validate_yearly_overtime_limit()

	def on_update(self):
		self.workflow_notification()

	def validate_duplicate(self):
		"""Check for duplicate overtime requests for the same employee and date."""
		filters = {
			"employee": self.employee,
			"date": self.date,
			"name": ["!=", self.name],
			"start_time": self.start_time,
			"end_time": self.end_time
		}
		exists_overtime_request = frappe.db.exists("Overtime Request", filters)
		if exists_overtime_request:
			frappe.throw(
				_("Already exists an Overtime Request {0} for employee {1} on {2}!".format(
					exists_overtime_request, self.employee, self.date
				))
			)

	def validate_leave_overlap(self):
		"""
		Block save if the employee has approved leave on the overtime date
		and this is a self-request. For manager requests, allow but log a comment.
		"""
		if not self.employee or not self.date:
			return

		overtime_date = getdate(self.date)

		LeaveApplication = frappe.qb.DocType("Leave Application")
		leave = (
			frappe.qb.from_(LeaveApplication)
			.select(LeaveApplication.name, LeaveApplication.leave_type)
			.where(LeaveApplication.employee == self.employee)
			.where(LeaveApplication.status == "Approved")
			.where(LeaveApplication.docstatus == 1)
			.where(LeaveApplication.from_date <= overtime_date)
			.where(LeaveApplication.to_date >= overtime_date)
		).run(as_dict=True)

		if not leave:
			return

		# Check if this is a self-request
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
		is_self_request = (self.requested_by == employee_user)

		if is_self_request:
			frappe.throw(
				_("You cannot create an Overtime Request on {0} as you have an approved {1} on this day.".format(
					frappe.format(overtime_date, {"fieldtype": "Date"}),
					leave[0].leave_type
				))
			)
		

	def calculate_overtime_hours(self):
		"""Calculate overtime hours from start_time and end_time.
		Handles overnight spans (e.g. 18:00 → 04:00 = 10 hours).
		"""
		if self.start_time and self.end_time:
			hours = time_diff_in_hours(self.end_time, self.start_time)
			# If negative, the overtime crosses midnight — add 24 hours
			if hours < 0:
				hours += 24
			self.overtime_hours = rounded(hours, 2)

	def calculate_yearly_overtime_hours(self):
		"""
		Calculate the cumulative yearly overtime hours for this employee
		in the current calendar year, including the current record's hours.
		"""
		if not self.employee or not self.overtime_hours:
			return

		# Get current calendar year boundaries
		overtime_date = getdate(self.date) if self.date else getdate()
		year_start = getdate(f"{overtime_date.year}-01-01")
		year_end = getdate(f"{overtime_date.year}-12-31")

		# Sum all approved/submitted overtime hours for this employee in the current year
		OvertimeRequest = frappe.qb.DocType("Overtime Request")
		result = (
			frappe.qb.from_(OvertimeRequest)
			.select(Sum(OvertimeRequest.overtime_hours).as_("total_hours"))
			.where(OvertimeRequest.employee == self.employee)
			.where(OvertimeRequest.docstatus == 1)
			.where(OvertimeRequest.date >= year_start)
			.where(OvertimeRequest.date <= year_end)
			.where(OvertimeRequest.name != self.name)
		).run(as_dict=True)

		past_hours = flt(result[0].total_hours) if result else 0.0
		self.yearly_overtime_hours = flt(past_hours + flt(self.overtime_hours), 2)

	def validate_yearly_overtime_limit(self):
		"""
		Block save if yearly overtime hours strictly exceed 180.
		Story 4: Fatal error when yearly_overtime_hours > 180.
		"""
		if flt(self.yearly_overtime_hours) > 180:
			frappe.throw(
				_("This request cannot be submitted. Adding these overtime hours "
				  "will exceed the maximum allowable limit of 180 overtime hours per year.")
			)

	def workflow_notification(self):
		"""
		Send notifications based on workflow state transitions.
		- Pending Acceptance by Employee: notify the employee
		- Pending Line Manager: notify the line manager
		- Pending Payroll Officer: handled by assignment rule
		- Completed: notify the requester
		- Rejected: notify the requester
		"""
		date = getdate(self.date).strftime("%d-%m-%Y")

		if self.workflow_state == "Pending Acceptance by Employee":
			message = _("{0} has Requested for {1} Hours Overtime on {2}.".format(
				self.full_name or self.employee, rounded(self.overtime_hours, 2), date
			))
			employee_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if employee_user:
				create_notification_log(message, message, [employee_user], self)

		elif self.workflow_state == "Pending Line Manager":
			reports_to_user = self.reports_to_user
			if reports_to_user:
				message = _("{0} has Requested for {1} Hours Overtime on {2}.".format(
					self.full_name or self.employee, rounded(self.overtime_hours, 2), date
				))
				create_notification_log(message, message, [reports_to_user], self)

		elif self.workflow_state == "Completed":
			message = _("The Overtime Request for {0} Hours on {1} has been Completed.".format(
				rounded(self.overtime_hours, 2), date
			))
			notify_user = self.requested_by or frappe.db.get_value("Employee", self.employee, "user_id")
			if notify_user:
				create_notification_log(message, message, [notify_user], self)

		elif self.workflow_state == "Rejected":
			message = _("The Overtime Request for {0} Hours on {1} has been Rejected.".format(
				rounded(self.overtime_hours, 2), date
			))
			notify_user = self.requested_by or frappe.db.get_value("Employee", self.employee, "user_id")
			if notify_user:
				create_notification_log(message, message, [notify_user], self)


@frappe.whitelist()
def check_leave_overlap(employee: str, overtime_date: str) -> dict:
	"""
	Check if the employee has an approved Leave Application
	that overlaps with the given overtime date.

	Returns:
		dict with keys:
			- has_leave (bool): True if overlap exists
			- employee_name (str): Full name of the employee
			- leave_type (str): Type of leave if overlap found
	"""
	overtime_date = getdate(overtime_date)

	LeaveApplication = frappe.qb.DocType("Leave Application")
	result = (
		frappe.qb.from_(LeaveApplication)
		.select(
			LeaveApplication.name,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
		)
		.where(LeaveApplication.employee == employee)
		.where(LeaveApplication.status == "Approved")
		.where(LeaveApplication.docstatus == 1)
		.where(LeaveApplication.from_date <= overtime_date)
		.where(LeaveApplication.to_date >= overtime_date)
	).run(as_dict=True)

	employee_name = frappe.db.get_value("Employee", employee, "employee_name") or ""

	if result:
		return {
			"has_leave": True,
			"employee_name": employee_name,
			"leave_type": result[0].leave_type,
			"leave_name": result[0].name,
		}

	return {
		"has_leave": False,
		"employee_name": employee_name,
		"leave_type": "",
		"leave_name": "",
	}


@frappe.whitelist()
def get_yearly_overtime_hours(employee: str, overtime_date: str, current_hours: float, current_name: str = "") -> float:
	"""
	Calculate the cumulative yearly overtime hours for an employee.
	Sum of all approved (docstatus=1) overtime hours in the current calendar year
	plus the current record's hours.

	Args:
		employee: Employee ID
		overtime_date: The date of the overtime request (to determine the year)
		current_hours: The current record's overtime hours
		current_name: The current record's name (to exclude from sum)

	Returns:
		float: Total yearly overtime hours including current
	"""
	overtime_date = getdate(overtime_date)
	year_start = getdate(f"{overtime_date.year}-01-01")
	year_end = getdate(f"{overtime_date.year}-12-31")

	OvertimeRequest = frappe.qb.DocType("Overtime Request")
	query = (
		frappe.qb.from_(OvertimeRequest)
		.select(Sum(OvertimeRequest.overtime_hours).as_("total_hours"))
		.where(OvertimeRequest.employee == employee)
		.where(OvertimeRequest.docstatus == 1)
		.where(OvertimeRequest.date >= year_start)
		.where(OvertimeRequest.date <= year_end)
	)

	if current_name:
		query = query.where(OvertimeRequest.name != current_name)

	result = query.run(as_dict=True)
	past_hours = flt(result[0].total_hours) if result else 0.0

	return flt(past_hours + flt(current_hours), 2)
