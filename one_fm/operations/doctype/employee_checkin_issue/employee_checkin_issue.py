# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, add_to_date, format_date, cstr
from frappe import _
from one_fm.api.notification import get_employee_user_id

from one_fm.api.utils import get_reports_to_employee_name
from one_fm.utils import (workflow_approve_reject, send_workflow_action_email)

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
		if self.workflow_state in ['Pending', 'Approved']:
			self.validate_attendance()
			self.validate_employee_checkin()

	def validate_attendance(self):
		attendance = frappe.db.exists('Attendance',{'attendance_date': self.date, 'employee': self.employee, 'docstatus': 1})
		if attendance:
			frappe.throw(_('There is an Attendance {0} exists for the \
			Employee {1} on {2}'.format(attendance, self.employee_name, format_date(self.date))), exc=ExistAttendance)

	def validate_employee_checkin(self):
		start_date = get_datetime(self.date)
		end_date = add_to_date(start_date, hours=23.9998)
		employee_checkin = frappe.db.exists('Employee Checkin',
			{'log_type': self.log_type, 'time': ["between", [start_date, end_date]], 'employee': self.employee}
		)
		if employee_checkin:
			frappe.throw(_('There is an Employee Checkin {0} exists for the \
			Employee {1} on {2}'.format(employee_checkin, self.employee_name, format_date(self.date))), exc=ExistCheckin)

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
			frappe.throw(_("{employee} has already created a Employee Checkin Issue for {log_type} on {date}.".format(employee=self.employee_name, log_type=self.log_type, date=date)))

	@frappe.whitelist()
	def create_issue(self):
		if not self.issue:
			issue_type = False
			if frappe.db.exists('Issue Type', {'name': 'Checkin Issue'}):
				issue_type = 'Checkin Issue'
			else:
				issue_type_doc = frappe.get_doc({"doctype": "Issue Type", "__newname": "Checkin Issue"}).insert()
				issue_type = issue_type_doc.name
			if issue_type:
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

	def on_update(self):
		if self.workflow_state == 'Approved':
			create_employee_checkin_for_employee_checkin_issue(self)
			workflow_approve_reject(self, [get_employee_user_id(self.employee)])

		if self.workflow_state == 'Pending':
			send_workflow_action_email(self, recipients=[get_employee_user_id(self.shift_supervisor)])

		if self.workflow_state in ['Rejected']:
			workflow_approve_reject(self, [get_employee_user_id(self.employee)])

def create_employee_checkin_for_employee_checkin_issue(employee_checkin_issue, from_api=False):
	"""
		Method to create Employee Checkin from the Employee Checkin Issue
		args:
			employee_checkin_issue: Object of Employee Checkin Issue
	"""
	# Get shift details for the employee
	shift_assignment = frappe.get_doc("Shift Assignment", employee_checkin_issue.assigned_shift)

	employee_checkin = frappe.new_doc('Employee Checkin')
	employee_checkin.employee = employee_checkin_issue.employee
	employee_checkin.log_type = employee_checkin_issue.log_type
	employee_checkin.time = shift_assignment.start_datetime if employee_checkin_issue.log_type == "IN" else shift_assignment.end_datetime
	employee_checkin.date = shift_assignment.start_date if employee_checkin_issue.log_type=='IN' else shift_assignment.end_datetime
	employee_checkin.skip_auto_attendance = False
	employee_checkin.employee_checkin_issue = employee_checkin_issue.name
	# The field shift in shift assignment is operations shift
	employee_checkin.operations_shift = shift_assignment.shift
	employee_checkin.shift_type = shift_assignment.shift_type
	# The field shift_type in shift assignment is shift type and in employee checkin the field shift is shift type
	employee_checkin.shift = shift_assignment.shift_type
	employee_checkin.shift_assignment = employee_checkin_issue.assigned_shift
	if employee_checkin_issue.latitude and employee_checkin_issue.longitude:
		employee_checkin.device_id = cstr(employee_checkin_issue.latitude)+","+cstr(employee_checkin_issue.longitude)
	if from_api:
		employee_checkin.flags.ignore_validate = True
	employee_checkin.save(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist()
def fetch_approver(employee):
	if employee:
		employee_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee}, order_by='creation desc',limit_page_length=1)
		if employee_shift:
			approver = get_reports_to_employee_name(employee)
			return employee_shift[0].name, approver, employee_shift[0].shift, employee_shift[0].shift_type

		frappe.throw("No approver found for {employee}".format(employee=employee))

# Approve pemding employee checkin issue before marking attendance
def approve_open_employee_checkin_issue(start_date, end_date):
	try:
		employee_checkin_issue_list = frappe.db.sql(f"""
			SELECT eci.name FROM `tabEmployee Checkin Issue` eci JOIN `tabShift Assignment` sa
			ON sa.name=eci.assigned_shift
			WHERE sa.start_date='{start_date}' and sa.end_date='{end_date}'
			AND eci.workflow_state='Pending' AND eci.docstatus=0
		""", as_dict=1)
		error_list = """"""
		for employee_checkin_issue in employee_checkin_issue_list:
			try:
				# Apply workflow
				employee_checkin_issue_doc = frappe.get_doc("Employee Checkin Issue", employee_checkin_issue.name)
				employee_checkin_issue_doc.db_set('workflow_state', 'Approved')
				employee_checkin_issue_doc.db_set('docstatus', 1)
				employee_checkin_issue_doc.add_comment("Info", "This record is System Aprroved")
				employee_checkin_issue_doc.reload()
				# Create checkin from employee checkin issue
				create_employee_checkin_for_employee_checkin_issue(employee_checkin_issue_doc, True)
			except Exception as e:
				error_list += str(e)+'\n\n'
		if error_list:frappe.log_error(error_list, 'Employee Checkin Issue')
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Employee Checkin Issue')
