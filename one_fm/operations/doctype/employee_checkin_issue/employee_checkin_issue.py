# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, add_to_date, format_date
from frappe import _
from one_fm.api.notification import get_employee_user_id
from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details
from one_fm.api.utils import get_reports_to_employee_name
from one_fm.api.v1.utils import response
from one_fm.utils import (
	workflow_approve_reject, send_workflow_action_email, get_approver
)

class ExistAttendance(frappe.ValidationError):
	pass

class ExistCheckin(frappe.ValidationError):
	pass

class ShiftDetailsMissing(frappe.ValidationError):
	pass

class EmployeeCheckinIssue(Document):
	def validate(self):
		self.check_shift_details_value()
		self.validate_attendance()
		self.validate_employee_checkin()
		self.validate_duplicate_record()
		self.validate_date()

	# This method validates the shift details availability for employee
	def check_shift_details_value(self):
		if not self.assigned_shift or not self.shift or not self.shift_supervisor or not self.shift_type:
			frappe.throw(_("Shift details are missing. Please make sure that the correct date is set."), exc=ShiftDetailsMissing)

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
			frappe.throw(
				_("Attendance record {0} already exists for {1} having Roster Type {2} on {3}.".format
					(
						attendance, self.employee_name, self.roster_type, format_date(self.date)
					)
				),
				exc=ExistAttendance
			)

	def validate_employee_checkin(self):
		start_date = get_datetime(self.date)
		end_date = add_to_date(start_date, hours=23.9998)
		employee_checkin = frappe.db.exists(
			"Employee Checkin",
			{
				"log_type": self.log_type,
				"time": ["between", [start_date, end_date]],
				"shift_assignment": self.assigned_shift,
				"employee": self.employee
			}
		)
		if employee_checkin:
			frappe.throw(
				_("Employee Checkin {0} of type {1} already exists for the shift assignment {2}".format(
						employee_checkin, self.log_type, self.assigned_shift
					)
				),
				exc=ExistCheckin
			)

	# This method validates any dublicate ECI for the employee on same day
	def validate_duplicate_record(self):
		if frappe.db.exists(
			"Employee Checkin Issue",
			{
				"employee": self.employee,
				"assigned_shift": self.assigned_shift,
				"log_type": self.log_type,
				"name": ["not in", [self.name]],
				"date": self.date
			}
		):
			msg = _(
				"{employee} has already created Employee Checkin Issue for {log_type} against the same Shift Assignment".format(
					employee=self.employee_name, log_type=self.log_type
				)
			)
			frappe.throw(msg)

	# This method validates the ECI date and avoid creating ECI for previous days
	def validate_date(self):
		if self.docstatus==0 and getdate(self.date) < getdate() and self.is_new():
			frappe.throw(_("Oops! You cannot create Employee Checkin Issue for a previous date."))

	@frappe.whitelist()
	def create_hd_ticket(self):
		if not self.ticket:
			ticket_type = self.get_ticket_type()
			ticket = frappe.new_doc('HD Ticket')
			ticket.subject = "Employee Checkin Issue - {0}".format(self.issue_type)
			ticket.raised_by = frappe.session.user
			doc_link = frappe.utils.get_url(self.get_url())
			description = ticket.subject + "<br/><p>The user found an issue in the app \
				and recorded in <a href='{0}'>Employee Checkin Issue</a>.</p>".format(doc_link)
			ticket.description = description
			ticket.ticket_type = ticket_type
			ticket.save(ignore_permissions=True)
			self.ticket = ticket.name
			self.save(ignore_permissions=True)
			self.reload()

	def get_ticket_type(self):
		if not frappe.db.exists('HD Ticket Type', {'name': 'Checkin Issue'}):
			ticket_type_doc = frappe.get_doc(
				{
					"doctype": "HD Ticket Type",
					"__newname": "Checkin Issue"
				}
			).insert()
			return ticket_type_doc.name
		return 'Checkin Issue'

@frappe.whitelist()
def fetch_approver(employee, date=None):
	if employee:
		shift_detail = {"assigned_shift":'',"shift_supervisor":'', "shift":'',"shift_type":''}
		filters={"employee":employee}
		if date:
			filters["start_date"] = getdate(date)
		employee_shift = frappe.get_list(
			"Shift Assignment",
			fields=["name", "shift", "shift_type"],
			filters=filters,
			order_by='creation desc',
			limit_page_length=1
		)
		if employee_shift and len(employee_shift)>0:
			approver = get_approver(employee)
			shift_detail['assigned_shift'] = employee_shift[0].name
			shift_detail['shift_supervisor'] = approver
			shift_detail['shift'] = employee_shift[0].shift
			shift_detail['shift_type'] = employee_shift[0].shift_type
			return shift_detail
		tail_end = ""
		if date:
			tail_end = "on {0}".format(date)
		frappe.throw("No shift assignment found for {employee} {tail_end}".format(employee=employee, tail_end=tail_end))

@frappe.whitelist()
def create_checkin_issue(employee, issue_type, log_type, latitude, longitude, reason):
	try:
		shift_detail = fetch_approver(employee)
		checkin_issue_doc = frappe.new_doc("Employee Checkin Issue")
		checkin_issue_doc.employee = employee
		checkin_issue_doc.date = getdate()
		checkin_issue_doc.issue_type = issue_type
		checkin_issue_doc.log_type = log_type
		checkin_issue_doc.longitude = longitude
		checkin_issue_doc.latitude = latitude
		checkin_issue_doc.assigned_shift = shift_detail['assigned_shift']
		checkin_issue_doc.shift_supervisor = shift_detail['shift_supervisor']
		checkin_issue_doc.shift = shift_detail['shift']
		checkin_issue_doc.shift_type = shift_detail['shift_type']
		if reason:
			checkin_issue_doc.issue_details = reason
		checkin_issue_doc.save(ignore_permissions=True)
		frappe.db.commit()
		response("Success", 200, checkin_issue_doc.as_dict())
	except:
		frappe.log_error(frappe.get_traceback(), 'Employee Checkin Issue')
		response("Bad Request", 400, None, "Employee Checkin Issue")

