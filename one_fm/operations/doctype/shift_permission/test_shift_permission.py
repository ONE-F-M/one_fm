# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from datetime import timedelta
from frappe.utils import (
	add_days, get_year_ending, get_year_start, now_datetime, nowdate
)
from one_fm.operations.doctype.shift_permission.shift_permission import (
	PermissionTypeandLogTypeError,
	ExistAttendance,
	ExistCheckin,
	ShiftDetailsMissing
)
from hrms.hr.doctype.attendance.attendance import mark_attendance

shift_permission_record = {
	"doctype": "Shift Permission",
	"reason": "Test Reason",
	"shift_supervisor": "_T-Employee-00001"
}

class TestShiftPermission(unittest.TestCase):
	def test_shift_permission_type(self):
		shift_permission = get_shift_permission_record()[0]

		shift_permission.log_type = "IN"
		shift_permission.permission_type = "Checkout Issue"
		self.assertRaises(PermissionTypeandLogTypeError, shift_permission.insert)
		shift_permission.permission_type = "Checkin Issue"
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

		shift_permission.log_type = "OUT"
		shift_permission.permission_type = "Checkin Issue"
		self.assertRaises(PermissionTypeandLogTypeError, shift_permission.insert)
		frappe.db.sql("delete from `tabShift Permission`")
		shift_permission.permission_type = "Checkout Issue"
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

		shift_permission.log_type = "OUT"
		shift_permission.permission_type = "Leave Early"
		shift_permission.leaving_time = ''
		self.assertRaises(frappe.MandatoryError, shift_permission.insert)
		frappe.db.sql("delete from `tabShift Permission`")
		shift_permission.leaving_time = '10:10:10'
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

		shift_permission.log_type = "IN"
		shift_permission.permission_type = "Arrive Late"
		shift_permission.arrival_time = ''
		self.assertRaises(frappe.MandatoryError, shift_permission.insert)
		frappe.db.sql("delete from `tabShift Permission`")
		shift_permission.arrival_time = '10:10:10'
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

	def test_validate_attendance(self):
		frappe.db.sql("delete from `tabAttendance`")
		shift_permission, employee = get_shift_permission_record()
		mark_attendance(employee, nowdate(), "Present")

		shift_permission.log_type = "IN"
		shift_permission.permission_type = "Checkin Issue"
		self.assertRaises(ExistAttendance, shift_permission.insert)
		shift_permission.date = add_days(nowdate(), 1)
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

	def test_validate_employee_checkin(self):
		frappe.db.sql("delete from `tabEmployee Checkin`")
		shift_permission, employee = get_shift_permission_record()
		employee_checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": now_datetime(),
				"device_id": "device1",
				"log_type": "IN",
			}
		).insert()

		shift_permission.log_type = "IN"
		shift_permission.permission_type = "Checkin Issue"
		self.assertRaises(ExistCheckin, shift_permission.insert)
		shift_permission.date = add_days(nowdate(), 1)
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

	def test_check_shift_details_value(self):
		date = nowdate()
		service_type = make_service_type()
		operations_shift = make_operations_shift()
		employee = make_employee("test_employee_@example.com", operations_shift, company="_Test Company")
		shift_assignment = make_shift_assignment(employee, date)

		shift_permission = frappe.copy_doc(shift_permission_record)
		shift_permission.employee = employee
		shift_permission.date = date
		shift_permission.log_type = "IN"
		shift_permission.permission_type = "Checkin Issue"
		self.assertRaises(ShiftDetailsMissing, shift_permission.insert)
		shift_permission.shift = operations_shift
		shift_permission.assigned_shift = shift_assignment.name
		shift_permission.shift_type = shift_assignment.shift_type
		self.assertTrue(shift_permission.insert())
		frappe.db.sql("delete from `tabShift Permission`")

def get_shift_permission_record():
	date = nowdate()
	service_type = make_service_type()
	operations_shift = make_operations_shift()
	employee = make_employee("test_employee_@example.com", operations_shift, company="_Test Company")
	shift_assignment = make_shift_assignment(employee, date)

	shift_permission = frappe.copy_doc(shift_permission_record)
	shift_permission.shift = operations_shift
	shift_permission.date = date
	shift_permission.assigned_shift = shift_assignment.name
	shift_permission.shift_type = shift_assignment.shift_type
	shift_permission.employee = employee

	return shift_permission, employee

def make_service_type():
	frappe.db.delete("Service Type")
	service_type = frappe.get_doc(
		{
			"doctype": "Service Type",
			"service_type": "_Test_Service_Type"
		}
	).insert()
	return service_type

def make_operations_shift():
	operations_shift = frappe.get_doc(
		{
			"doctype": "Operations Shift",
			"service_type": "_Test_Service_Type",
			"shift_number": "2345"
		}
	)
	operations_shift.insert()
	return operations_shift.name

def make_employee(user, operations_shift, company=None, **kwargs):
	frappe.db.delete("Employee")
	if not frappe.db.get_value("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": user,
				"new_password": "password",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": "Employee"}],
			}
		).insert()
	if not frappe.db.get_value("Employee", {"user_id": user}):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"naming_series": "EMP-",
				"first_name": user,
				"last_name": "LN",
				"employee_name": "Emp Name",
				"one_fm_first_name_in_arabic": "FNA",
				"one_fm_last_name_in_arabic": "LNA",
				"one_fm_basic_salary": "100",
				"shift": operations_shift,
				"company": company or erpnext.get_default_company(),
				"user_id": user,
				"date_of_birth": "1990-05-08",
				"date_of_joining": "2013-01-01",
				"department": frappe.get_all("Department", fields="name")[0].name,
				"gender": "Female",
				"company_email": user,
				"prefered_contact_email": "Company Email",
				"prefered_email": user,
				"status": "Active",
				"employment_type": "Intern",
			}
		)
		if kwargs:
			employee.update(kwargs)
		employee.insert()
		return employee.name
	else:
		frappe.db.set_value("Employee", {"user_id": user}, "status", "Active")
		return frappe.db.get_value("Employee", {"user_id": user})

def make_shift_assignment(employee, start_date, shift_type=None, end_date=None):
	if not shift_type:
		shift_type = setup_shift_type().name

	shift_assignment = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"shift_type": shift_type,
			"company": "_Test Company",
			"employee": employee,
			"start_date": start_date,
			"end_date": end_date,
		}
	).insert()

	shift_assignment.submit()
	return shift_assignment

def setup_shift_type(**args):
	frappe.db.delete("Shift Type")
	args = frappe._dict(args)
	date = nowdate()

	shift_type = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"__newname": args.shift_type or "_Test Shift",
			"start_time": "08:00:00",
			"end_time": "12:00:00",
			"enable_auto_attendance": 1,
			"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
			"working_hours_calculation_based_on": "First Check-in and Last Check-out",
			"begin_check_in_before_shift_start_time": 60,
			"allow_check_out_after_shift_end_time": 60,
			"process_attendance_after": add_days(date, -2),
			"last_sync_of_checkin": now_datetime() + timedelta(days=1),
		}
	)

	holiday_list = "Employee Checkin Test Holiday List"
	if not frappe.db.exists("Holiday List", "Employee Checkin Test Holiday List"):
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": "Employee Checkin Test Holiday List",
				"from_date": get_year_start(date),
				"to_date": get_year_ending(date),
			}
		).insert()
		holiday_list = holiday_list.name

	shift_type.holiday_list = holiday_list
	shift_type.update(args)
	shift_type.save()

	return shift_type
