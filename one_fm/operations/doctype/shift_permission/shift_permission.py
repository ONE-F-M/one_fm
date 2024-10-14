# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, format_date
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow
from frappe import _
from frappe.desk.form.assign_to import add, remove
from one_fm.api.notification import create_notification_log, get_employee_user_id
from one_fm.utils import has_super_user_role, get_approver

class PermissionTypeandLogTypeError(frappe.ValidationError):
	pass

class ExistAttendance(frappe.ValidationError):
	pass

class ExistCheckin(frappe.ValidationError):
	pass

class ShiftDetailsMissing(frappe.ValidationError):
	pass

class ShiftPermission(Document):
	def validate(self):
		self.check_shift_details_value()
		self.validate_date()
		self.validate_record()
		self.validate_approver()
		if self.workflow_state in ['Pending Approver', 'Approved']:
			self.validate_attendance()
		if not self.title:
			self.title = self.emp_name

	def validate_attendance(self):
		attendance = frappe.db.exists('Attendance',{'attendance_date': self.date, 'employee': self.employee, 'docstatus': 1})
		if attendance:
			frappe.throw(_('There is an Attendance {0} exists for the Employee {1} on {2}'.format(attendance, self.emp_name, format_date(self.date))), exc=ExistAttendance)
	
	def on_update(self):
		self.update_shift_assignment_checkin()
		self.assign_to_owner()

	# This method validates the shift details availability for employee
	def check_shift_details_value(self):
		if not self.assigned_shift or not self.shift or not self.shift_supervisor or not self.shift_type:
			frappe.throw(_("Shift details are missing. Please make sure date is correct."), exc=ShiftDetailsMissing)

	# This method validates the permission date and avoid creating permission for previous days
	def validate_date(self):
		if getdate(self.date) < getdate():
			frappe.throw(_("Please note that shift permission can not be created for past date")) if self.is_new() else frappe.throw("Please note that shift permission can not be updated to a past date")

	# This method validates any dublicate permission for the employee on same day
	def validate_record(self):
		date = getdate(self.date).strftime('%d-%m-%Y')
		if self.docstatus==0 and frappe.db.exists("Shift Permission", {
			"employee": self.employee, "date":self.date, "assigned_shift": self.assigned_shift,
			"workflow_state":"Pending Approver", 'name':['!=', self.name]
			}):
			frappe.throw(_("{employee} has already applied for permission on {date}.".format(employee=self.emp_name,date=date)))

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
			frappe.throw(message, exc=frappe.MandatoryError)

	def after_insert(self):
		if self.log_type == 'IN':
			frappe.msgprint(_("Please ensure checkin once arriving the site!"), alert=True, indicator='orange')
		if self.log_type == 'OUT':
			frappe.msgprint(_("Please ensure checkout before leaving the site!"), alert=True, indicator='orange')

	def send_notification(self):
		date = getdate(self.date).strftime('%d-%m-%Y')
		user = get_employee_user_id(self.shift_supervisor)
		subject = _("{employee} has applied for permission on {date}.".format(employee=self.emp_name, date=date))
		message = _("{employee} has applied for permission on {date}.".format(employee=self.emp_name, date=date))
		create_notification_log(subject, message, [user], self)

	def validate_approver(self):
		if self.workflow_state in ["Approved", "Rejected"]:
			if has_super_user_role(frappe.session.user):
				return
			#if frappe.session.user not in [self.approver_user_id, 'administrator', 'Administrator']:
			#	frappe.throw(_("This document can only be approved/rejected by the approver."))

	def on_submit(self):
		employee_user = frappe.get_value('Employee', self.employee, 'user_id')
		subject = _('Your shift permission {0} has been {1} by {2}'.format(self.name, self.workflow_state, self.approver_name))
		if self.workflow_state == 'Approved':
			if employee_user:
				create_notification_log(subject, subject, [employee_user], self)

		if self.workflow_state == 'Rejected':
			message = False
			if self.log_type == 'IN':
				message = _('Your shift permission has been rejected, Please checkin once you arrive to the site before [half way mark] or your attendance will be marked absent!')
			if self.log_type == 'OUT':
				message = _('Your shift permission has been rejected, Please make sure to checkout!')
			if message and employee_user:
				create_notification_log(subject, message, [employee_user], self)

	def on_cancel(self):
		pass


	def update_shift_assignment_checkin(self) -> None:
		if self.workflow_state == "Approved" and self.get_doc_before_save().workflow_state != "Approved":
			if self.assigned_shift:
				if self.log_type == "IN":
					if self.arrival_time:
						date_time = datetime.strptime(self.date + " " + self.arrival_time, '%Y-%m-%d %H:%M:%S')
						frappe.db.sql("""
										UPDATE `tabShift Assignment`
										SET start_datetime = %s
										WHERE name = %s
									""", (date_time, self.assigned_shift))

						frappe.db.sql("""
										UPDATE `tabEmployee Checkin`
										SET shift_actual_start = %s, late_entry = 0
										WHERE shift_assignment = %s
										AND log_type = %s
									""", (date_time, self.assigned_shift, self.log_type))

				else:
					if self.leaving_time:
						date_time = datetime.strptime(self.date + " " + self.leaving_time, '%Y-%m-%d %H:%M:%S')
						frappe.db.sql("""
										UPDATE `tabShift Assignment`
										SET end_datetime = %s
										WHERE name = %s
									""", (date_time, self.assigned_shift))

						frappe.db.sql("""
										UPDATE `tabEmployee Checkin`
										SET shift_actual_end = %s, early_exit = 0
										WHERE shift_assignment = %s
										AND log_type = %s
									""", (date_time, self.assigned_shift, self.log_type))

			frappe.db.commit()

	def assign_to_owner(self):
		# Assign back to owner if Shift permission is Returned to Draft state from Pending Approver
		if not self.get("__unsaved"):
			if self.workflow_state == "Draft" and self.get_doc_before_save().workflow_state == "Pending Approver":
				# Remove approver's assignment
				remove(self.doctype, self.name, frappe.session.user, ignore_permissions=False)

				# Assign back to document owner
				add({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': [self.owner],
					'description': (_(f"Shift Permission: {self.name} has been returned to Draft. Please check and review."))
				})
			
			if self.workflow_state == "Pending Approver" and self.get_doc_before_save().workflow_state == "Draft":
				# Remove doc owner's assignment
				remove(self.doctype, self.name, self.owner, ignore_permissions=False)
		
@frappe.whitelist()
def fetch_approver(employee, date=None):
	if employee:
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
		if employee_shift and len(employee_shift) > 0:
			approver = get_approver(employee)
			return {
				'shift_assignment':employee_shift[0].name, 
				'approver':approver, 
				'shift':employee_shift[0].shift, 
				'shift_type':employee_shift[0].shift_type
			}
	
	frappe.throw("No shift assigned to {employee}".format(employee=employee))


# approve open shift permission before marking attendance
def approve_open_shift_permission(start_date, end_date):
	try:
		shift_permissions = frappe.db.sql(f"""
			SELECT sp.name FROM `tabShift Permission` sp JOIN `tabShift Assignment` sa
			ON sa.name=sp.assigned_shift
			WHERE sa.start_date ='{start_date}' and sa.end_date <='{end_date}'
			AND sa.is_replaced = 0
			AND sp.workflow_state='Pending Approver' AND sp.docstatus=0
		""", as_dict=1)
		# apply workflow
		error_list = """"""
		for i in shift_permissions:
			try:
				shift_permission = frappe.get_doc("Shift Permission", i.name)
				create_checkin(shift_permission)
				apply_workflow(shift_permission, 'Approve')
			except Exception as e:
				error_list += str(e)+'\n\n'
		if error_list:frappe.log_error(error_list, 'Shift Permission')
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Shift Permission')

def create_checkin(shift_permission):
	# create checkin from shift permission
	shift_assignment = frappe.get_doc("Shift Assignment", shift_permission.assigned_shift)
	start_time = shift_assignment.start_datetime
	end_time = shift_assignment.end_datetime

	#get the last checkin log ordered by time.
	log = frappe.db.sql(f""" SELECT * FROM `tabEmployee Checkin`
						WHERE employee='{shift_permission.employee}'
						AND time between '{start_time}' AND '{end_time}'
						ORDER BY time DESC LIMIT 1;
	""",as_dict=1)
	#If log exists and the last checkin log type is same as the shift permission logtype,
	# create checkin log opposite to it.
	if log and log[0].log_type == shift_permission.log_type:
		ec = frappe.new_doc('Employee Checkin')
		ec.employee = shift_permission.employee
		ec.log_type = "IN" if shift_permission.log_type == "OUT" else "OUT"
		ec.skip_auto_attendance = 0
		ec.time = log[0].time
		ec.date = shift_assignment.start_date if shift_permission.log_type=='OUT' else shift_assignment.end_datetime
		ec.early_exit = 0
		ec.late_entry = 0
		ec.flags.ignore_validate = True
		ec.save(ignore_permissions=True)
		frappe.db.commit()

	if not frappe.db.exists("Employee Checkin", {
		'shift_permission':shift_permission.name
		}):
		if not shift_permission.workflow_state == 'Approved':
			shift_permission.db_set('workflow_state', "Approved")
			shift_permission.db_set("docstatus", 1)
			shift_permission.reload()
			frappe.db.commit()
		# Get shift details for the employee shift_assignment = frappe.get_doc("Shift Assignment", shift_permission.assigned_shift)
		employee_checkin = frappe.new_doc('Employee Checkin')
		employee_checkin.employee = shift_permission.employee
		employee_checkin.log_type = shift_permission.log_type
		employee_checkin.time = shift_assignment.start_datetime if shift_permission.log_type == "IN" else shift_assignment.end_datetime
		employee_checkin.date = shift_assignment.start_date if shift_permission.log_type=='IN' else shift_assignment.end_datetime
		employee_checkin.skip_auto_attendance = 0
		employee_checkin.shift_assignment = shift_permission.assigned_shift
		employee_checkin.shift_permission = shift_permission.name
		employee_checkin.operations_shift = shift_assignment.shift
		employee_checkin.shift_type = shift_assignment.shift_type
		employee_checkin.shift_actual_start = shift_assignment.start_datetime
		employee_checkin.shift_actual_end = shift_assignment.end_datetime
		employee_checkin.flags.ignore_validate = True
		employee_checkin.save(ignore_permissions=True)
		employee_checkin.db_set('creation', str(shift_assignment.start_datetime)+'.000000' if employee_checkin.log_type == "IN" else str(shift_assignment.end_datetime)+'.999999')
		employee_checkin.db_set('actual_time', shift_assignment.start_datetime if employee_checkin.log_type == "IN" else shift_assignment.end_datetime)
		frappe.db.commit()
