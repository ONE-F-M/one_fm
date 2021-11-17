# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, getdate, cstr
from one_fm.api.notification import create_notification_log, get_employee_user_id
from frappe import _
from frappe.utils import rounded

class OvertimeRequest(Document):

	def validate(self):
		self.validate_duplicate()
		self.calculate_overtime_hours()
		self.validate_mandatory()

	def validate_duplicate(self):
		filters = {'request_type': self.request_type, 'employee': self.employee, 'date': self.date}
		if self.request_type == 'Head Office':
			filters['start_time'] = self.start_time
			filters['end_time'] = self.end_time

		elif self.request_type == 'Operations':
			filters['shift'] = self.shift
			filters['post_type'] = self.post_type

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
				reports_to = frappe.db.get_value("Employee",{'name':self.employee},['reports_to'])
				supervisor_name = frappe.db.get_value("Employee", reports_to, "employee_name")
				employee_user_id = get_employee_user_id(self.employee)
				subject = _("{employee} has Requested for {hours} Hours Overtime on {date}.".format(employee=supervisor_name, hours=rounded(self.overtime_hours,1), date=date))
				message = _("{employee} has Requested for {hours} Hours Overtime on {date}.".format(employee=supervisor_name, hours=rounded(self.overtime_hours,1), date=date))
				create_notification_log(subject, message, [employee_user_id], self)

			if self.request_type == "Operations":
				shift_name = frappe.db.get_value("Employee",{'name':self.employee},['shift'])
				supervisor_name = frappe.db.get_value("Operations Shift",{'name':shift_name},['supervisor_name'])
				employee_user_id = get_employee_user_id(self.employee)
				subject = _("{employee} has Requested for Overtime Shift on {date}.".format(employee=supervisor_name, date=date))
				message = _("{employee} has Requested for Overtime Shift on {date}.".format(employee=supervisor_name, date=date))
				create_notification_log(subject, message, [employee_user_id], self)

		if self.workflow_state == "Request Accepted":
			if self.request_type == "Head Office":
				reports_to, employee_name = frappe.db.get_value("Employee",{'name':self.employee},['reports_to', 'employee_name'])
				supervisor_user_id = get_employee_user_id(reports_to)
				subject = _("{employee} has Accepted The Overtime Request for {hours} Hours on {date}.".format(employee=employee_name, hours=rounded(self.overtime_hours,1), date=date))
				message = _("{employee} has Accepted The Overtime Request for {hours} Hours on {date}.".format(employee=employee_name, hours=rounded(self.overtime_hours,1), date=date))
				create_notification_log(subject, message, [supervisor_user_id], self)

			if self.request_type == "Operations":
				shift_name, employee_name = frappe.db.get_value("Employee",{'name':self.employee},['shift', 'employee_name'])
				supervisor= frappe.db.get_value("Operations Shift",{'name':shift_name},['supervisor'])
				supervisor_user_id = get_employee_user_id(supervisor)
				subject = _("{employee} has Accepted The Overtime Request on {date}.".format(employee=employee_name, date=date))
				message = _("{employee} has Accepted The Overtime Request on {date}.".format(employee=employee_name, date=date))
				create_notification_log(subject, message, [supervisor_user_id], self)
				self.create_employee_schedule()

		if self.workflow_state == "Request Rejected":
			if self.request_type == "Head Office":
				reports_to, employee_name = frappe.db.get_value("Employee",{'name':self.employee},['reports_to', 'employee_name'])
				supervisor_user_id = get_employee_user_id(reports_to)
				supervisor_user_id = get_employee_user_id(reports_to)
				subject = _("{employee} has Rejected The Overtime Request for {hours} Hours on {date}.".format(employee=employee_name, hours=rounded(self.overtime_hours,1), date=date))
				message = _("{employee} has Rejected The Overtime Request for {hours} Hours on {date}.".format(employee=employee_name, hours=rounded(self.overtime_hours,1), date=date))
				create_notification_log(subject, message, [supervisor_user_id], self)

			if self.request_type == "Operations":
				shift_name, employee_name = frappe.db.get_value("Employee",{'name':self.employee},['shift', 'employee_name'])
				supervisor= frappe.db.get_value("Operations Shift",{'name':shift_name},['supervisor'])
				supervisor_user_id = get_employee_user_id(supervisor)
				subject = _("{employee} has Rejected The Overtime Request on {date}.".format(employee=employee_name, date=date))
				message = _("{employee} has Rejected The Overtime Request on {date}.".format(employee=employee_name, date=date))
				create_notification_log(subject, message, [supervisor_user_id], self)

	# Method creating employee Schedula on The Acceptance of OT Request for Operations Employee
	def create_employee_schedule(self):
		"""
		setting data << employee, shift, post type, date, employee_availability, Roster Type >>
		"""
		if not frappe.db.exists("Employee Schedule",{'employee':self.employee, 'date':self.date, 'shift':self.operation_shift, 'post_type':self.post_type, 'roster_type':"Over-Time"}):
			print("created successfully")
			employee_schedule = frappe.new_doc("Employee Schedule")
			employee_schedule.employee = self.employee
			employee_schedule.date = cstr(self.date)
			employee_schedule.employee_availability = "Working"
			employee_schedule.post_type = self.post_type
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
			if not self.post_type:
				mandatory_fields.append('Post Type')
			self.set_mendatory_fields(mandatory_fields)

	# This Method throw the mandatory fields message to the user
	def set_mendatory_fields(self, mandatory_fields):
		if len(mandatory_fields) > 0:
			message= 'Mandatory Fields required For Overtime Request Form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)
