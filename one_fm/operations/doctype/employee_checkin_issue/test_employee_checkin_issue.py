# Copyright (c) 2023, omar jaber and Contributors
# See license.txt

from __future__ import unicode_literals

import frappe
import unittest

from datetime import timedelta
from frappe.utils import (
	add_days, get_year_ending, get_year_start, now_datetime, nowdate
)
from one_fm.operations.doctype.employee_checkin_issue.employee_checkin_issue import (
	ExistAttendance,
	ExistCheckin,
	ShiftDetailsMissing
)

from one_fm.operations.doctype.shift_permission.test_shift_permission import (
	make_employee, make_shift_assignment, make_service_type, make_operations_shift
)

from hrms.hr.doctype.attendance.attendance import mark_attendance

employee_checkin_issue_record = {
	"doctype": "Employee Checkin Issue",
	"shift_supervisor": "_T-Employee-00001"
}

class TestEmployeeCheckinIssue(unittest.TestCase):
	def test_validate_attendance(self):
		frappe.db.sql("delete from `tabAttendance`")
		employee_checkin_issue, employee = get_employee_checkin_issue_record()
		mark_attendance(employee, nowdate(), "Present")

		employee_checkin_issue.log_type = "IN"
		employee_checkin_issue.permission_type = "Checkin Issue"
		self.assertRaises(ExistAttendance, employee_checkin_issue.insert)
		employee_checkin_issue.date = add_days(nowdate(), 1)
		self.assertTrue(employee_checkin_issue.insert())
		frappe.db.sql("delete from `tabEmployee Checkin Issue`")

	def test_validate_employee_checkin(self):
		frappe.db.sql("delete from `tabEmployee Checkin`")
		employee_checkin_issue, employee = get_employee_checkin_issue_record()
		employee_checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": now_datetime(),
				"device_id": "device1",
				"log_type": "IN",
			}
		).insert()

		employee_checkin_issue.log_type = "IN"
		employee_checkin_issue.permission_type = "Checkin Issue"
		self.assertRaises(ExistCheckin, employee_checkin_issue.insert)
		employee_checkin_issue.date = add_days(nowdate(), 1)
		self.assertTrue(employee_checkin_issue.insert())
		frappe.db.sql("delete from `tabEmployee Checkin Issue`")

	def test_check_shift_details_value(self):
		date = nowdate()
		service_type = make_service_type()
		operations_shift = make_operations_shift()
		employee = make_employee("test_employee_@example.com", operations_shift, company="_Test Company")
		shift_assignment = make_shift_assignment(employee, date)

		employee_checkin_issue = frappe.copy_doc(employee_checkin_issue_record)
		employee_checkin_issue.employee = employee
		employee_checkin_issue.date = date
		employee_checkin_issue.log_type = "IN"
		employee_checkin_issue.permission_type = "Checkin Issue"
		self.assertRaises(ShiftDetailsMissing, employee_checkin_issue.insert)
		employee_checkin_issue.shift = operations_shift
		employee_checkin_issue.assigned_shift = shift_assignment.name
		employee_checkin_issue.shift_type = shift_assignment.shift_type
		self.assertTrue(employee_checkin_issue.insert())
		frappe.db.sql("delete from `tabEmployee Checkin Issue`")

def get_employee_checkin_issue_record():
	date = nowdate()
	service_type = make_service_type()
	operations_shift = make_operations_shift()
	employee = make_employee("test_employee_@example.com", operations_shift, company="_Test Company")
	shift_assignment = make_shift_assignment(employee, date)

	employee_checkin_issue = frappe.copy_doc(employee_checkin_issue_record)
	employee_checkin_issue.shift = operations_shift
	employee_checkin_issue.date = date
	employee_checkin_issue.assigned_shift = shift_assignment.name
	employee_checkin_issue.shift_type = shift_assignment.shift_type
	employee_checkin_issue.employee = employee

	return employee_checkin_issue, employee
