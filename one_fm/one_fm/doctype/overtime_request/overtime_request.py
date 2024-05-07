# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, getdate, cstr
from one_fm.api.notification import create_notification_log, get_employee_user_id
from frappe import _
from frappe.utils import rounded
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor, get_shift_supervisor_user

class OvertimeRequest(Document):

	def validate(self):
		self.validate_duplicate()
		self.calculate_overtime_hours()
		self.validate_mandatory()

	def validate_duplicate(self):
		filters = {'request_type': self.request_type, 'employee': self.employee, 'date': self.date, 'name': ['!=', self.name]}
		if self.request_type == 'Head Office':
			filters['start_time'] = self.start_time
			filters['end_time'] = self.end_time

		elif self.request_type == 'Operations':
			filters['shift'] = self.shift
			filters['operations_role'] = self.operations_role

		exists_overtime_request = frappe.db.exists('Overtime Request', filters)
		if exists_overtime_request:
			frappe.throw(_('Already exists a Overtime Request {0} for employee {1} on {2}!'.format(exists_overtime_request, self.employee, self.date)))


	def on_update(self):
		self.workflow_notification()


	def calculate_overtime_hours(self):
		"""This method sets the `overtime_hours` for Head Office employee"""
		if self.request_type == "Head Office" and self.start_time and self.end_time:
			hours=time_diff_in_hours(self.end_time,self.start_time)
			self.overtime_hours = rounded(hours,1)

	def workflow_notification(self):
		"""
		Explicit Explanation:
		---------------------
		The method is checking `workflow_state` and notifying the requested employee upon `request_type`:
		For `Head Office`: `report_to` is the one needed to be notified upon employee response (Accept or Reject)
		For `Operations`: Shift Supervisor `supervisor_name` is the one needed to be notified upon employee response (Accept or Reject)

		On Acceptance of OT request for `Operations` employee, Employee Schedule record will be created with the shift details mentioned in the OT request
		"""
		date = getdate(self.date).strftime('%d-%m-%Y')
		if self.workflow_state == "Pending":
			if self.request_type == "Head Office":
				message = "{employee} has Requested for {hours} Hours Overtime on {date}."
				self.send_non_shift_employee_notification(message, date)

			if self.request_type == "Operations":
				message = "{employee} has Requested for Overtime Shift on {date}."
				self.send_shift_employee_notification(message, date)

		if self.workflow_state == "Request Accepted":
			if self.request_type == "Head Office":
				message = "{employee} has Accepted The Overtime Request for {hours} Hours on {date}."
				self.send_reports_to_notification(message, date)

			if self.request_type == "Operations":
				message = "{employee} has Accepted The Overtime Request on {date}."
				self.send_shift_supervisor_notification(message, date)

		if self.workflow_state == "Request Rejected":
			if self.request_type == "Head Office":
				message = "{employee} has Rejected The Overtime Request for {hours} Hours on {date}."
				self.send_reports_to_notification(message, date)

			if self.request_type == "Operations":
				message = "{employee} has Rejected The Overtime Request on {date}."
				self.send_shift_supervisor_notification(message, date)

	def send_non_shift_employee_notification(self, message, date):
		employee = frappe.db.get_value(
			"Employee",
			{"name": self.employee},
			["reports_to", "user_id"],
			as_dict = True
		)
		if employee.user_id and employee.reports_to:
			reports_to_name = frappe.db.get_value("Employee", employee.reports_to, "employee_name")
			message = _(message.format(employee=reports_to_name, hours=rounded(self.overtime_hours,1), date=date))
			create_notification_log(message, message, [employee.user_id], self)

	def send_reports_to_notification(self, message, date):
		employee = frappe.db.get_value(
			"Employee",
			{"name": self.employee},
			["reports_to", "employee_name"],
			as_dict = True
		)
		if employee.reports_to:
			reports_to_user = get_employee_user_id(employee.reports_to)
			message = _(message.format(employee=employee.employee_name, hours=rounded(self.overtime_hours,1), date=date))
			create_notification_log(message, message, [reports_to_user], self)

	def send_shift_employee_notification(self, message, date):
		employee = frappe.db.get_value(
			"Employee",
			{"name": self.employee},
			["shift", "user_id"],
			as_dict = True
		)
		if employee.user_id and employee.shift:
			supervisor = get_shift_supervisor(employee.shift)
			if supervisor:
				supervisor_name = frappe.db.get_value("Employee", supervisor, "employee_name")
				message = _(message.format(employee=supervisor_name, date=date))
				create_notification_log(message, message, [employee.user_id], self)

	def send_shift_supervisor_notification(self, message, date):
		employee = frappe.db.get_value(
			"Employee",
			{"name": self.employee},
			["employee_name", "shift"],
			as_dict = True
		)
		if employee.shift:
			supervisor_user = get_shift_supervisor_user(employee.shift)
			if supervisor_user:
				message = _(message.format(employee=employee.employee_name, date=date))
				create_notification_log(message, message, [supervisor_user], self)

	# Method creating employee Schedula on The Acceptance of OT Request for Operations Employee
	def create_employee_schedule(self):
		"""
		setting data << employee, shift, post type, date, employee_availability, Roster Type >>
		"""
		if not frappe.db.exists("Employee Schedule",{'employee':self.employee, 'date':self.date, 'shift':self.operation_shift, 'operations_role':self.operations_role, 'roster_type':"Over-Time"}):
			print("created successfully")
			employee_schedule = frappe.new_doc("Employee Schedule")
			employee_schedule.employee = self.employee
			employee_schedule.date = cstr(self.date)
			employee_schedule.employee_availability = "Working"
			employee_schedule.operations_role = self.operations_role
			employee_schedule.shift = self.shift
			employee_schedule.roster_type = "Over-Time"
			employee_schedule.save(ignore_permissions=True)

	# This method checks mandatory fields per Request Type
	def validate_mandatory(self):
		mandatory_fields = []
		if self.request_type == "Head Office":
			if not self.start_time:
				mandatory_fields.append('Start Time')
			if not self.end_time:
				mandatory_fields.append('End Time')
			self.set_mendatory_fields(mandatory_fields)

		elif self.request_type == "Operations":
			if not self.shift:
				mandatory_fields.append('Shift')
			if not self.operations_role:
				mandatory_fields.append('Operations Role')
			self.set_mendatory_fields(mandatory_fields)

		# FILTER OUT OPERATIONS REQUEST TYPE
		if(self.request_type=='Operations'):
			frappe.throw("""Request type <b>Operations</b> not allowed.
				Only <b>Head Office</b> is permitted.""")

	# This Method throw the mandatory fields message to the user
	def set_mendatory_fields(self, mandatory_fields):
		if len(mandatory_fields) > 0:
			message= 'Mandatory Fields required For Overtime Request Form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)
