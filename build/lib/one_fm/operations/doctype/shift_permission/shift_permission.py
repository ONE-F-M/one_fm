# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _
from one_fm.api.notification import create_notification_log, get_employee_user_id
class ShiftPermission(Document):
	def validate(self):
		self.check_permission_type()
		self.check_shift_details_value()
		self.validate_date()
		self.validate_record()

	def check_permission_type(self):
		if self.permission_type == "Arrive Late":
			field_list = [{'Arrival Time':'arrival_time'}]
			self.set_mandatory_fields(field_list)
		if self.permission_type == "Leave Early":
			field_list = [{'Leaving Time':'leaving_time'}]
			self.set_mandatory_fields(field_list)

	# This method validates the shift details availability for employee
	def check_shift_details_value(self):
		if not self.assigned_shift or not self.shift or not self.shift_supervisor or not self.shift_type:
			frappe.throw(_("Shift details are missing. Please make sure date is correct."))

	# This method validates the permission date and avoid creating permission for previous days
	def validate_date(self):
		if self.docstatus==0 and getdate(self.date) < getdate():
			frappe.throw(_("Oops! You cannot apply for permission for a previous date."))
	
	# This method validates any dublicate permission for the employee on same day
	def validate_record(self):
		date = getdate(self.date).strftime('%d-%m-%Y')
		if self.docstatus==0 and frappe.db.exists("Shift Permission", {"employee": self.employee, "date":self.date, "assigned_shift": self.assigned_shift, "permission_type": self.permission_type, "workflow_state":"Pending"}):
			frappe.throw(_("{employee} has already applied for permission to {type} on {date}.".format(employee=self.emp_name, type=self.permission_type.lower(), date=date)))

	# This method will display the mandatory fields for the user
	def set_mandatory_fields(self,field_list):
		mandatory_fields = []
		for fields in field_list:
			for field in fields:
				if not self.get(fields[field]):
					mandatory_fields.append(field)
        
		if len(mandatory_fields) > 0:
			message= 'Mandatory fields required in Shift Permission<br><br><ul>'
			for mandatory_field in mandatory_fields:
				message += '<li>' + mandatory_field +'</li>'
			message += '</ul>'
			frappe.throw(message)

	def after_insert(self):
		self.send_notification()

	def send_notification(self):
		date = getdate(self.date).strftime('%d-%m-%Y')
		user = get_employee_user_id(self.shift_supervisor)
		subject = _("{employee} has applied for permission to {type} on {date}.".format(employee=self.emp_name, type=self.permission_type.lower(), date=date))
		message = _("{employee} has applied for permission to {type} on {date}.".format(employee=self.emp_name, type=self.permission_type.lower(), date=date))
		create_notification_log(subject, message, [user], self)
