# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import now_datetime, add_to_date
from one_fm.processor import sendemail

class EmployeePaidHolidayTimesheet(Document):
	def on_update(self):
		if self.status == "Open" and self.docstatus < 1:
			# notify approver about creation
			self.notify_approver()

	def notify_approver(self):
		if self.approver:
			self.notify({
				# for post in messages
				"message": "Employee Paid Holiday Timesheet is Opened by {0}, please Approve or Reject".format(self.employee_name),
				"message_to": self.approver,
				# for email
				"subject": "Employee Paid Holiday Timesheet is Opened by {0}".format(self.employee_name)
			})

	def notify_employee(self, status=False):
		employee = frappe.get_doc("Employee", self.employee)
		if not employee.user_id:
			return

		status = status if status else self.status
		self.notify({
			# for post in messages
			"message": "Your Employee Paid Holiday Timesheet {0} by {1}".format(status, self.employee_name),
			"message_to": employee.user_id,
			# for email
			"subject": "Your Employee Paid Holiday Timesheet {0} by {1}".format(status, self.employee_name),
			"notify": "employee"
		})

	def notify(self, args):
		args = frappe._dict(args)
		# args -> message, message_to, subject
		contact = args.message_to
		if not isinstance(contact, list):
			if not args.notify == "employee":
				contact = frappe.get_doc('User', contact).email or contact

		sender      	    = dict()
		sender['email']     = frappe.get_doc('User', frappe.session.user).email
		sender['full_name'] = frappe.utils.get_fullname(sender['email'])

		try:
			sendemail(
				recipients = contact,
				sender = sender['email'],
				subject = args.subject,
				message = args.message,
			)
			frappe.msgprint(_("Email sent to {0}").format(contact))
		except frappe.OutgoingEmailError:
			pass

	def on_submit(self):
		if self.status == "Open":
			frappe.throw(_("Only Employee Paid Holiday Timesheet with status 'Approved' and 'Rejected' can be submitted"))
		if self.status == "Approved":
			if self.hours_per_day == 0:
				frappe.throw(_("Only Employee Paid Holiday Timesheet with hour per day greater than zero can be Approved"))
			self.create_timesheet_for_items()
		self.notify_employee()
		self.reload()

	def on_cancel(self):
		self.cancel_timesheets()
		frappe.db.set_value('Employee Paid Holiday Timesheet', self.name, 'status', 'Cancelled')
		self.notify_employee('Cancelled')
		self.reload()

	def cancel_timesheets(self):
		for item in self.items:
			if item.timesheet:
				frappe.get_doc('Timesheet', item.timesheet).cancel()

	def create_timesheet_for_items(self):
		for item in self.items:
			if not item.timesheet:
				ts = frappe.new_doc('Timesheet')
				ts.employee = self.employee
				time_logs = ts.append('time_logs')
				activity_type = frappe.db.exists('Activity Type', {'name': 'Paid Holiday Timesheet'})
				if not activity_type:
					activity_type = frappe.new_doc('Activity Type')
					activity_type.activity_type = "Paid Holiday Timesheet"
					activity_type.save(ignore_permissions = True)
					time_logs.activity_type = activity_type.name
				else:
					time_logs.activity_type = activity_type
				time_logs.from_time = add_to_date(item.date, as_datetime=True)
				time_logs.hours = self.hours_per_day
				time_logs.to_time = add_to_date(item.date, hours=self.hours_per_day, as_datetime=True)
				ts.submit()
				frappe.db.set_value('Employee Paid Holiday Timesheet Item', item.name, 'timesheet', ts.name)
