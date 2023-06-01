# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils import nowdate, add_to_date, cstr

class AttendanceCheck(Document):
	pass

@frappe.whitelist()
def create_attendance_check():
	date = add_to_date(nowdate(), days=-1)
	data = fetch_data(date)

	for d in data:
		doc = frappe.new_doc("Attendance Check")
		doc.employee = d
		doc.date = date
		if data[d]['shift_assignment'] == 0:
			doc.has_shift_assignment = 1
			doc.shift_assignment = frappe.get_doc("Shift Assignment", {'employee': d, 'start_date':date})
			
		if data[d]['checkin']== 0:
			doc.has_checkin_record = 1
			emp_checkin = frappe.db.sql("""SELECT name, log_type FROM `tabEmployee Checkin` empChkin
							WHERE
							date(empChkin.time)='{date}'
							AND employee = '{employee}'""".format(date=cstr(date), employee=d), as_dict=1)
			for checkin in emp_checkin:
				if checkin.log_type == "IN":
					doc.checkin_record = frappe.get_doc("Employee Checkin", checkin.name)
				if checkin.log_type == "OUT":
					doc.checkout_record = frappe.get_doc("Employee Checkin", checkin.name)
		if data[d]['attendance'] == 0:
			doc.has_the_attendance_for_the_marked = 1
			doc.attendance =  frappe.get_value("Attendance", {'employee': d, 'attendance_date':date}, ['name'])

		if frappe.db.exists("Shift Permission", {'employee': d, 'date':date}):
			doc.has_shift_pemission = 1
			doc.shift_permission = frappe.get_value("Shift Permission", {'employee': d, 'date':date}, ['name'])
		
		if frappe.db.exists("Attendance Request", {'employee': d, 'date':date}):
			doc.has_attendance_request = 1
			doc.attendance_request = frappe.get_value("Attendance Request", {'employee': d, 'date':date}, ['name'])

		doc.insert()
		doc.submit()
	frappe.db.commit()

def fetch_data(date):
	active_employee = frappe.get_list("Employee", {"status":"Active"},['name'])

	active_employee = [emp.name for emp in active_employee]
	no_shift_assignment = fetch_no_shift_assignment(date, active_employee)
	no_checkin = fetch_no_checkin_record(date, active_employee)
	no_attendance = fetch_no_attendance(date, active_employee)

	data = {}
	processed_values = set()

	for value in no_shift_assignment + no_checkin + no_attendance:  # Merge all lists and create a set of unique values
		if value not in processed_values:
			data[value] = {
				'shift_assignment': int(value in no_shift_assignment),
				'checkin': int(value in no_checkin),
				'attendance': int(value in no_attendance)
			}
			processed_values.add(value)

	return data


def fetch_no_shift_assignment(date, employees):
	shift_assignment = get_assigned_shift(date)
	day_off = get_days_off(date)
	
	no_sa = [e for e in employees if e not in shift_assignment]
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

def fetch_no_attendance(date, employees):
	shift_assignment =  get_assigned_shift(date)
	attendance = frappe.db.sql("""SELECT employee FROM `tabAttendance`
							WHERE attendance_date='{date}'
							AND employee in {employees}""".format(date=cstr(date), employees=tuple(employees)), as_dict=1)
	attendance = [emp.employee for emp in attendance]

	no_attendance =  [e for e in employees if e not in shift_assignment and e not in attendance]
	return no_attendance

