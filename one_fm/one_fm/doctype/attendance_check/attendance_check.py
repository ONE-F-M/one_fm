# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils import nowdate, add_to_date, cstr

class AttendanceCheck(Document):
	pass

def create_attendance_check():
	active_employee = frappe.get_list("Employee", {"status":"Active"},['name'])
	date = add_to_date(nowdate(), days=-1)

	active_employee = [emp.name for emp in active_employee]
	no_shift_assignment = fetch_no_shift_assignment(date, active_employee)
	no_checkin = fetch_no_checkin_record(date, active_employee)
	attendance = fetch_attendance(date, active_employee)

def fetch_no_shift_assignment(date, employees):
	shift_assignment = get_assigned_shift(date)
	day_off = get_days_off(date)
	
	no_sa = [e for e in employees if e not in shift_assignment and e not in day_off]
	return no_sa

def get_assigned_shift(date):
	shift_assignment = frappe.get_list("Shift Assignment", {'start_date':date}, ['employee'])
	shift_assignment = [emp.employee for emp in shift_assignment]
	return shift_assignment

def get_days_off(date):
	day_off_emp_se = frappe.get_list("Employee Schedule", {'date':date, 'employee_availability':'Day Off'}, ['employee'])
	day_off_emp_se = [emp.employee for emp in day_off_emp_se]
	day_off_emp_nse = frappe.db.sql("""SELECT name as employee, holiday_list from `tabEmployee` E
				WHERE E.shift_working = 0 AND E.status='Active' AND E.attendance_by_timesheet != 1
				AND EXISTS(SELECT * from `tabHoliday` h
					WHERE
						h.parent = E.holiday_list
					AND h.holiday_date = '{date}')
					""".format(date=date), as_dict=1)
	day_off_emp_nse = [emp.employee for emp in day_off_emp_nse]
	day_off_emp_se.extend(day_off_emp_nse)

	return day_off_emp_se

def fetch_no_checkin_record(date, employees):
	shift_assignment = get_assigned_shift(date)
	checkin_employee = get_checkin(date)

	no_checkin = [e for e in employees if e not in shift_assignment and e not in checkin_employee]
	return no_checkin

def get_checkin(date):
	checkin = frappe.db.sql("""SELECT DISTINCT employee FROM `tabEmployee Checkin` empChkin
							WHERE
							date(empChkin.time)='{date}'""".format(date=cstr(date)), as_dict=1)
	checkin = [emp.employee for emp in checkin]
	return checkin

def fetch_attendance(date, employees):
	attendance = frappe.db.sql("""SELECT name, employee FROM `tabAttendance`
							WHERE attendance_date='{date}'
							AND employee in {employees}""".format(date=cstr(date), employees=tuple(employees)), as_dict=1)
	return attendance

