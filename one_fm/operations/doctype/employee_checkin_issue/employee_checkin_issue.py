# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, add_to_date, format_date
from frappe import _
from one_fm.api.utils import get_reports_to_employee_name

class ExistAttendance(frappe.ValidationError):
	pass

class ExistCheckin(frappe.ValidationError):
	pass

class ShiftDetailsMissing(frappe.ValidationError):
	pass

class EmployeeCheckinIssue(Document):
	def validate(self):
		self.check_shift_details_value()
		self.validate_date()
		self.validate_duplicate_record()
		if self.workflow_state in {'Pending Approval', 'Approved'}:
			self.validate_attendance()
			self.validate_employee_checkin()

	# This method validates the shift details availability for employee
	def check_shift_details_value(self):
		if not self.assigned_shift or not self.shift or not self.shift_supervisor or not self.shift_type:
			frappe.throw(_("Shift details are missing. Please make sure date is correct."), exc=ShiftDetailsMissing)

	# This method validates the ECI date and avoid creating ECI for previous days
	def validate_date(self):
		if self.docstatus==0 and getdate(self.date) < getdate() and self.is_new():
			frappe.throw(_("Oops! You cannot create a Employee Checkin Issue for a previous date."))

	# This method validates any dublicate ECI for the employee on same day
	def validate_duplicate_record(self):
		date = getdate(self.date).strftime('%d-%m-%Y')
		if frappe.db.exists("Employee Checkin Issue", {"employee": self.employee, "date":self.date,
			"assigned_shift": self.assigned_shift, "log_type": self.log_type, "name": ["not in", [self.name]]}):
			msg = _(
				"{employee} has already created a Employee Checkin Issue for {log_type} on {date}.".format(
					employee=self.employee_name, log_type=self.log_type, date=date
				)
			)
			frappe.throw(msg)

	def validate_attendance(self):
		attendance = frappe.db.exists(
			"Attendance",
			{
				"attendance_date": self.date,
				"employee": self.employee,
				"docstatus": 1,
				"roster_type": self.roster_type
			}
		)
		if attendance:
			frappe.throw(_('There is an Attendance {0} exists for the \
			Employee {1} on {2}'.format(attendance, self.employee_name, format_date(self.date))), exc=ExistAttendance)

	def validate_employee_checkin(self):
		start_date = get_datetime(self.date)
		end_date = add_to_date(start_date, hours=23.9998)
		employee_checkin = frappe.db.exists(
			"Employee Checkin",
			{
				"log_type": self.log_type,
				"time": ["between", [start_date, end_date]],
				"employee": self.employee,
				"roster_type": self.roster_type
			}
		)
		if employee_checkin:
			frappe.throw(_('There is an Employee Checkin {0} exists for the \
			Employee {1} on {2}'.format(employee_checkin, self.employee_name, format_date(self.date))), exc=ExistCheckin)


	@frappe.whitelist()
	def create_issue(self):
		if not self.issue:
			issue_type = self.get_issue_type()
			issue = frappe.new_doc('Issue')
			issue.subject = "Employee Checkin Issue - {0}".format(self.issue_type)
			issue.raised_by = frappe.session.user
			doc_link = frappe.utils.get_url(self.get_url())
			description = issue.subject + "<br/><p>The user found an issue in the app \
				and recorded in <a href='{0}'>Employee Checkin Issue</a>.</p>".format(doc_link)
			issue.description = description
			issue.issue_type = issue_type
			issue.save(ignore_permissions=True)
			self.issue = issue.name
			self.save(ignore_permissions=True)
			self.reload()

	def get_issue_type(self):
		if not frappe.db.exists('Issue Type', {'name': 'Checkin Issue'}):
			issue_type_doc = frappe.get_doc(
				{
					"doctype": "Issue Type",
					"__newname": "Checkin Issue"
				}
			).insert()
			return issue_type_doc.name
		return 'Checkin Issue'

@frappe.whitelist()
def fetch_approver(employee):
	if employee:
		employee_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee}, order_by='creation desc',limit_page_length=1)
		if employee_shift:
			approver = get_reports_to_employee_name(employee)
			return employee_shift[0].name, approver, employee_shift[0].shift, employee_shift[0].shift_type

		frappe.throw("No approver found for {employee}".format(employee=employee))
