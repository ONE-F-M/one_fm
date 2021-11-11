# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, getdate, cstr
from one_fm.api.notification import create_notification_log, get_employee_user_id
from frappe import _
from frappe.utils import rounded

class OvertimeRequest(Document):
	
	def on_update(self):
		self.calculate_overtime_hours()
		self.workflow_notification()
		self.validate_mandatory()

	def calculate_overtime_hours(self):
		"""This method sets the `overtime_hours` for Head Office employee"""
		if self.request_type == "Head Office":
			if self.start_time and self.end_time:
				hours=time_diff_in_hours(self.end_time,self.start_time)
				self.db_set('overtime_hours',rounded(hours,1))

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
				supervisor_name = self.get_employee_name(reports_to)
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

	# Method returns employee full name 
	def get_employee_name(self, employee_code):
		"""
		Param: `employee_code` (eg: HR-EMP-00004)
		Return: `employee_name` (eg: Amna Hatem Alshawa)
		"""
		return frappe.db.get_value("Employee", employee_code, "employee_name")

	# Method creating employee Schedula on The Acceptance of OT Request for Operations Employee
	def create_employee_schedule(self):
		"""
		setting data << employee, shift, post type, date, employee_availability, Roster Type >>
		"""
		if not frappe.db.exists("Employee Schedule",{'employee':self.employee, 'date':self.date, 'shift':self.operation_shift, 'post_type':self.post_type, 'roster_type':"Over-Time"}):
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
		if self.workflow_state == "Pending":
			if self.request_type == "Head Office":
				field_list = [{'Start Time':'start_time'},{'End Time':'end_time'}]
				self.set_mendatory_fields(field_list)

			if self.request_type == "Operations":
				field_list = [{'Shift':'shift'},{'Post Type':'post_type'}]
				self.set_mendatory_fields(field_list)

	# This Method throw the mandatory fields message to the user
	def set_mendatory_fields(self, field_list):
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
					mandatory_fields.append(field)
        
		if len(mandatory_fields) > 0:
			message= 'Mandatory Fields required For Overtime Request Form<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)


