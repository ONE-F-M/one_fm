# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now, cint, get_datetime
from frappe.model.document import Document
from frappe import _
import datetime

from erpnext.hr.doctype.shift_assignment.shift_assignment import get_actual_start_end_datetime_of_shift
from erpnext.hr.utils import validate_active_employee

def mark_attendance_and_link_log(logs, attendance_status, attendance_date, working_hours=None, late_entry=False, early_exit=False, shift=None, operations_shift=None):
	"""Creates an attendance and links the attendance to the Employee Checkin.
	Note: If attendance is already present for the given date, the logs are marked as skipped and no exception is thrown.

	:param logs: The List of 'Employee Checkin'.
	:param attendance_status: Attendance status to be marked. One of: (Present, Absent, Half Day, Skip). Note: 'On Leave' is not supported by this function.
	:param attendance_date: Date of the attendance to be created.
	:param working_hours: (optional)Number of working hours for the given date.
	"""
	project = post_type = None
	log_names = [x.name for x in logs]
	employee = logs[0].employee
	shift_assignment = frappe.get_list("Shift Assignment", {"employee":employee, 'start_date': ['<=', attendance_date], "shift_type":shift}, ["project", "post_type"])
	if shift_assignment:
		project = shift_assignment[0].project
		post_type = shift_assignment[0].post_type
	if attendance_status == 'Skip':
		frappe.db.sql("""update `tabEmployee Checkin`
			set skip_auto_attendance = %s
			where name in %s""", ('1', log_names))
		return None
	elif attendance_status in ('Present', 'Absent', 'Half Day'):
		employee_doc = frappe.get_doc('Employee', employee)
		if not frappe.db.exists('Attendance', {'employee':employee, 'attendance_date':attendance_date, 'docstatus':('!=', '2')}):
			doc_dict = {
				'doctype': 'Attendance',
				'employee': employee,
				'attendance_date': attendance_date,
				'status': attendance_status,
				'working_hours': working_hours,
				'company': employee_doc.company,
				'shift': shift,
				'late_entry': late_entry,
				'early_exit': early_exit,
				#'in_time': in_time,
				#'out_time': out_time,
				'operations_shift':operations_shift,
				'project': project,
				'post_type': post_type
			}
			attendance = frappe.get_doc(doc_dict).insert()
			attendance.submit()
			frappe.db.sql("""update `tabEmployee Checkin`
				set attendance = %s
				where name in %s""", (attendance.name, log_names))
			return attendance
		else:
			frappe.db.sql("""update `tabEmployee Checkin`
				set skip_auto_attendance = %s
				where name in %s""", ('1', log_names))
			return None
	else:
		frappe.throw(_('{} is an invalid Attendance Status.').format(attendance_status))
