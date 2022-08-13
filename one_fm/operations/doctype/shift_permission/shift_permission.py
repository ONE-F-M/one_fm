# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _
from one_fm.api.notification import create_notification_log, get_employee_user_id
from erpnext.hr.doctype.shift_assignment.shift_assignment import get_shift_details
from one_fm.api.tasks import get_action_user
from one_fm.api.utils import get_reports_to_employee_name
from one_fm.utils import (workflow_approve_reject, send_workflow_action_email)

class ShiftPermission(Document):
	def validate(self):
		self.check_permission_type()
		self.check_shift_details_value()
		self.validate_date()
		self.validate_record()
		if not self.title:
			self.title = self.emp_name

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

	def on_update(self):
		if self.workflow_state == 'Approved':
			create_employee_checkin_for_shift_permission(self)
			workflow_approve_reject(self, [get_employee_user_id(self.employee)])

		if self.workflow_state == 'Pending':
			send_workflow_action_email(self, recipients=[get_employee_user_id(self.shift_supervisor)])

		if self.workflow_state in ['Rejected']:
			workflow_approve_reject(self, [get_employee_user_id(self.employee)])

def create_employee_checkin_for_shift_permission(shift_permission):
	"""
		Method to create Employee Checkin from the Shift Permission
		args:
			shift_permission: Object of Shift Permission
	"""
	if not frappe.db.get_single_value("HR and Payroll Additional Settings", 'validate_shift_permission_on_employee_checkin')\
		and not frappe.db.exists('Employee Checkin', {'shift_permission': shift_permission.name, 'docstatus': 1}):
		log_type = False
		if shift_permission.permission_type in ["Arrive Late", "Forget to Checkin", "Checkin Issue"]:
			log_type = "IN"
		elif shift_permission.permission_type in ["Leave Early", "Forget to Checkout", "Checkout Issue"]:
			log_type = "OUT"
		if not log_type:
			return False

		# Get shift details for the employee
		shift_details = get_shift_details(shift_permission.shift_type, getdate(shift_permission.date))

		employee_checkin = frappe.new_doc('Employee Checkin')
		employee_checkin.employee = shift_permission.employee
		employee_checkin.log_type = log_type
		employee_checkin.shift = shift_permission.shift_type
		employee_checkin.time = shift_details.start_datetime if log_type == "IN" else shift_details.end_datetime
		employee_checkin.skip_auto_attendance = False
		employee_checkin.operations_shift = shift_permission.shift
		employee_checkin.shift_assignment = shift_permission.assigned_shift
		employee_checkin.shift_permission = shift_permission.name
		employee_checkin.save(ignore_permissions=True)

@frappe.whitelist()
def fetch_approver(employee):
	if employee:
		employee_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee}, order_by='creation desc',limit_page_length=1)
		if employee_shift:
			approver = get_reports_to_employee_name(employee)
			return employee_shift[0].name, approver, employee_shift[0].shift, employee_shift[0].shift_type

		frappe.throw("No approver found for {employee}".format(employee=employee))