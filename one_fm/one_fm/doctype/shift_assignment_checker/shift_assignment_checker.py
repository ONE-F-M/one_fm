# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
	now_datetime,nowtime, cstr, getdate, get_datetime, cint, add_to_date, today, add_days, now, get_url_to_form
)
from datetime import datetime
from one_fm.utils import ( production_domain, get_today_leaves)
import json
from frappe.desk.form.assign_to import add as add_assignment


class ShiftAssignmentChecker(Document):
	def on_submit(self):
		add_assignment({
				'doctype': self.doctype,
				'name': self.name,
				'assign_to': [self.attendance_manager],
				'description': (f"{self.roster_type} Shift Assignment for the {self.employee_name} was not created for {self.start_date}. Kindly, take action. ")
			})


@frappe.whitelist()
def run_shift_assignment_checker():
	date = cstr(getdate())
	now = datetime.strptime("20-02-2024 06:00:00", "%d-%m-%Y %H:%M:%S")  #now_datetime()
	print(now)
	now_time = datetime.strptime("08:00:00", "%H:%M:%S").time()
	print(now_time)
	shift_request = frappe.db.sql("""
			SELECT * from `tabShift Request` SR
				WHERE '{date}' BETWEEN SR.from_date AND SR.to_date
				AND SR.assign_day_off = 0
				AND SR.workflow_state = 'Approved'
				AND SR.employee
					NOT IN (Select employee from `tabShift Assignment` tSA
					WHERE tSA.employee = SR.employee
					AND tSA.start_date='{date}')
				AND SR.shift_type IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time = '{now_time}')
				AND SR.employee
					IN (Select employee from `tabEmployee` E
					WHERE E.name = SR.employee
					AND E.status = 'Active')""".format(now_time=now_time,date=cstr(date), now=now), as_dict=1)
	
	roster = frappe.db.sql("""
			SELECT * from `tabEmployee Schedule` ES
				WHERE ES.start_datetime = '{now}'
				AND ES.employee_availability = "Working"
				AND ES.employee
					NOT IN (Select employee from `tabShift Assignment` tSA
					WHERE tSA.employee = ES.employee
					AND tSA.start_date='{date}')
				AND ES.employee
					IN (Select employee from `tabEmployee` E
					WHERE E.name = ES.employee
					AND E.status = 'Active')""".format(date=cstr(date), now=now), as_dict=1)

	non_shift = frappe.db.sql("""SELECT @roster_type := 'Basic' as roster_type, name as employee, employee_name, department, holiday_list, default_shift as shift_type, checkin_location, shift, site from `tabEmployee` E
				WHERE E.shift_working = 0
				AND E.status='Active'
				AND E.attendance_by_timesheet != 1
				AND E.default_shift IN(
					SELECT name from `tabShift Type` st
					WHERE st.start_time = '{now_time}')
				AND E.employee
					NOT IN (Select employee from `tabShift Assignment` tSA
					WHERE tSA.employee = E.employee
					AND tSA.start_date='{date}')
				AND NOT EXISTS(SELECT * from `tabHoliday` h
					WHERE
						h.parent = E.holiday_list
					AND h.holiday_date = '{date}')""".format(now_time=now_time, date=cstr(date)), as_dict=1)
	# non_shift = fetch_non_shift(date, "PM")
	if non_shift:
		roster.extend(non_shift)
	
	if shift_request:
		roster_emp = shift_request
		employee_list = [i.employee for i in shift_request]
		for r in roster:
			if r.employee not in employee_list:
				roster_emp.append(r)

	if len(roster)>0:
		create_shift_assignmen_checker(roster = roster, date = date)

def create_shift_assignmen_checker(roster, date):
	# try:
	attendance_manager = frappe.db.get_value("Employee", {"name":frappe.get_doc("ONEFM General Setting").get("attendance_manager")},['user_id'])
	for schedule in roster:
		print(schedule)
		shift_assignment_checker = frappe.new_doc("Shift Assignment Checker")
		shift_assignment_checker.start_date = date
		shift_assignment_checker.employee = schedule.employee
		shift_assignment_checker.employee_name = schedule.employee_name
		shift_assignment_checker.department = schedule.department
		shift_assignment_checker.operations_role = schedule.operations_role
		shift_assignment_checker.shift = schedule.shift if schedule.get('doctype') !="Shift Request" else schedule.get('operations_shift')
		shift_assignment_checker.site = schedule.site
		shift_assignment_checker.project = schedule.project
		shift_assignment_checker.shift_type = schedule.shift_type
		shift_assignment_checker.operations_role = schedule.operations_role
		shift_assignment_checker.post_abbrv = schedule.post_abbrv
		shift_assignment_checker.roster_type = schedule.roster_type
		shift_assignment_checker.site_location =  frappe.db.get_value("Operations Site",{'name':schedule.site},["site_location"])
		if attendance_manager:
			print(attendance_manager)
			shift_assignment_checker.attendance_manager = attendance_manager
		if schedule.doctype == 'Shift Request':
			shift_assignment_checker.shift_request = schedule.name
			if schedule.check_in_site and schedule.check_out_site:
				shift_assignment_checker.check_in_site = shift_assignment_checker.check_in_site
				shift_assignment_checker.check_out_site = shift_assignment_checker.check_out_site
		shift_assignment_checker.submit()
	# except Exception:
	# 	# Log all the errors except the OverlappingShiftError(ValidationError)
	# 	frappe.log_error(frappe.get_traceback(), "Create Shift Assignment Checker")

@frappe.whitelist()
def create_shift_assignment(doc):
	doc = json.loads(doc)
	print(doc.get('employee'))
	shift_assignment = frappe.new_doc("Shift Assignment")
	shift_assignment.employee = doc.get('employee')
	shift_assignment.employee_name = doc.get('employee_name')
	shift_assignment.department = doc.get('department')
	shift_assignment.start_date =  doc.get('start_date')
	shift_assignment.operations_role = doc.get('operations_role')
	shift_assignment.shift = doc.get('operations_shift')
	shift_assignment.site = doc.get('site')
	shift_assignment.project = doc.get('project')
	shift_assignment.shift_type = doc.get('shift_type')
	shift_assignment.operations_role = doc.get('operations_role')
	shift_assignment.post_abbrv = doc.get('post_abbrv')
	shift_assignment.roster_type = doc.get('roster_type')
	shift_assignment.site_location = doc.get('site_location')
	if doc.get('shift_request'):
		if doc.get('check_in_site') and doc.get('check_out_site'):
			shift_assignment.check_in_site = doc.get('check_in_site')
			shift_assignment.check_out_site = doc.get('doc.check_out_site')
	shift_assignment.submit()

	frappe.set_value("Shift Assignment Checker", doc.get('name'), 'shift_assignment_created', 1)
	frappe.db.commit()