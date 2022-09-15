from pandas.core.indexes.datetimes import date_range
import frappe
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate
import itertools
import pandas as pd
import numpy as np
import time
from frappe import _
import json
import multiprocessing 
import os
from multiprocessing.pool import ThreadPool as Pool
from itertools import product
from one_fm.api.notification import create_notification_log

@frappe.whitelist(allow_guest=True)
def get_staff(assigned=1, employee_id=None, employee_name=None, company=None, project=None, site=None, shift=None, department=None, designation=None):
	date = cstr(add_to_date(nowdate(), days=1))
	conds = ""

	if employee_name:
		conds += 'and emp.employee_name="{name}" '.format(name=employee_name)
	if department:
		conds += 'and emp.department="{department}" '.format(department=department)	
	if designation:
		conds += 'and emp.designation="{designation}" '.format(designation=designation)
	if company:
		conds += 'and emp.company="{company}" '.format(company=company)
		
	if project:
		conds += 'and emp.project="{project}" '.format(project=project)
	if site:
		conds += 'and emp.site="{site}" '.format(site=site)
	if shift:
		conds += 'and emp.name="{shift}" '.format(shift=shift)

	if not cint(assigned):
		data = frappe.db.sql("""
			select 
				distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.project
			from `tabEmployee` as emp, `tabUser` as usr
			where 
			emp.project is NULL
			and emp.site is NULL
			and emp.shift is NULL
			and emp.user_id=usr.name
			{conds}
		""".format(date=date, conds=conds), as_dict=1)
		return data

	data = frappe.db.sql("""
		select 
			distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site, emp.project
		from `tabEmployee` as emp, `tabUser` as usr
		where 
		emp.project is not NULL
		and emp.site is not NULL
		and emp.shift is not NULL
		and emp.user_id=usr.name
		{conds}
	""".format(date=date, conds=conds), as_dict=1)
	return data

@frappe.whitelist(allow_guest=True)
def get_staff_filters_data():
	company = frappe.get_list("Company", limit_page_length=9999, order_by="name asc")
	projects = frappe.get_list("Project", limit_page_length=9999, order_by="name asc")
	sites = frappe.get_list("Operations Site", limit_page_length=9999, order_by="name asc")
	shifts = frappe.get_list("Operations Shift", limit_page_length=9999, order_by="name asc")
	departments = frappe.get_list("Department", limit_page_length=9999, order_by="name asc")
	designations = frappe.get_list("Designation", limit_page_length=9999, order_by="name asc")

	return {
		"company": company,
		"projects": projects,
		"sites": sites,
		"shifts": shifts,
		"departments": departments,
		"designations": designations
	}


@frappe.whitelist()
def get_roster_view(start_date, end_date, assigned=0, scheduled=0, employee_search_id=None, employee_search_name=None, project=None, site=None, shift=None, department=None, operations_role=None, designation=None, isOt=None, limit_start=0, limit_page_length=9999):
	start = time.time()
		
	master_data, formatted_employee_data, post_count_data, employee_filters, additional_assignment_filters={}, {}, {}, {}, {}
	operations_roles_list = []
	employees = []

	filters = {
		'date': ['between', (start_date, end_date)]
	}

	if operations_role:
		filters.update({'operations_role': operations_role})		

	if employee_search_id:
		employee_filters.update({'employee_id': employee_search_id})

	if employee_search_name:
		employee_filters.update({'employee_name': ("like", "%" + employee_search_name + "%")})
		additional_assignment_filters.update({'employee_name': ("like", "%" + employee_search_name + "%")})
	if project:
		employee_filters.update({'project': project})
		additional_assignment_filters.update({'project': project})
	if site:
		employee_filters.update({'site': site})	
		additional_assignment_filters.update({'site': site})
	if shift:
		employee_filters.update({'shift': shift})
		additional_assignment_filters.update({'shift': shift})	
	if department:
		employee_filters.update({'department': department})	


	#--------------------- Fetch Employee list ----------------------------#
	if isOt:
		employee_filters.update({'employee_availability' : 'Working'})
		employees = frappe.db.get_list("Employee Schedule", employee_filters, ["distinct employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
		master_data.update({'total' : len(employees)})
		employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
		employee_filters.pop('employee_availability')
	else: 
		employee_filters.update({'status': 'Active'})
		if designation:
			employee_filters.update({'designation' : designation})
		employees = frappe.db.get_list("Employee", employee_filters, ["employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
		employees_asa = frappe.db.get_list("Additional Shift Assignment", additional_assignment_filters, ["distinct employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True)
		if len(employees_asa) > 0:
			employees.extend(employees_asa)
			employees = filter_redundant_employees(employees)
		master_data.update({'total': len(employees)})
		employee_filters.pop('status', None)	
		employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})

	if employee_search_name:
		employee_filters.pop('employee_name')
	if employee_search_id:
		employee_filters.pop('employee_id')	
	if department:
		employee_filters.pop('department', None)
	if operations_role:
		employee_filters.update({'operations_role': operations_role})
	if designation:
		employee_filters.pop('designation', None)

	#------------------- Fetch Operations Roles ------------------------#
	operations_roles_list = frappe.db.get_list("Post Schedule", employee_filters, ["distinct operations_role", "post_abbrv"], ignore_permissions=True)
	if operations_role:
		employee_filters.pop('operations_role', None)
	employee_filters.pop('date')
	employee_filters.pop('post_status')


	#------------------- Fetch Employee Schedule --------------------#
	for key, group in itertools.groupby(employees, key=lambda x: (x['employee'], x['employee_name'])):
		filters.update({'date': ['between', (start_date, end_date)], 'employee': key[0]})
		if isOt:
			filters.update({'roster_type' : 'Over-Time'})	
		schedules = frappe.db.get_list("Employee Schedule",filters, ["employee", "employee_name", "date", "operations_role", "post_abbrv",  "shift", "roster_type", "employee_availability", "day_off_ot"], order_by="date asc, employee_name asc", ignore_permissions=True)
		if isOt:
			filters.pop("roster_type", None)

		attendances = frappe.db.get_list("Attendance", {'attendance_date': ['between', (start_date, add_to_date(cstr(getdate()), days=-1))], 'employee': key[0]}, ["status", "attendance_date"], ignore_permissions=True)	
		schedule_list = []
		schedule = {}
		default_shift = frappe.db.get_value("Employee", {'employee': key[0]}, ["shift"])

		for date in	pd.date_range(start=start_date, end=end_date):
			if date < getdate() and any(cstr(attendance.attendance_date) == cstr(date).split(" ")[0] for attendance in attendances):
				attendance = next((attendance for attendance in attendances if cstr(attendance.attendance_date) == cstr(date).split(" ")[0]), {})			
				schedule = {
					'employee': key[0],
					'employee_name': key[1],
					'date': cstr(date).split(" ")[0],
					'attendance': attendance.status
				}
				
			elif not any(cstr(schedule.date) == cstr(date).split(" ")[0] for schedule in schedules):
				schedule = {
					'employee': key[0],
					'employee_name': key[1],
					'date': cstr(date).split(" ")[0]
				}
			else:
				schedule = next((sch for sch in schedules if cstr(sch.date) == cstr(date).split(" ")[0]), {})
				if schedule.shift and schedule.shift != default_shift:
					schedule.update({'asa': default_shift})
			schedule_list.append(schedule)
		formatted_employee_data.update({key[1]: schedule_list})

	master_data.update({'employees_data': formatted_employee_data})


	#----------------- Get Operations Role count and check fill status -------------------#
	for key, group in itertools.groupby(operations_roles_list, key=lambda x: (x['post_abbrv'], x['operations_role'])):
		post_list = []
		post_filters = employee_filters
		post_filters.update({'date':  ['between', (start_date, end_date)], 'operations_role': key[1]})
		post_filled_count = frappe.db.get_list("Employee Schedule",["name", "employee", "date"] ,{'date':  ['between', (start_date, end_date)],'operations_role': key[1] }, order_by="date asc", ignore_permissions=True)
		post_filters.update({"post_status": "Planned"})
		post_schedule_count = frappe.db.get_list("Post Schedule", ["name", "date"], post_filters, ignore_permissions=True)
		post_filters.pop("post_status", None)

		for date in	pd.date_range(start=start_date, end=end_date):
			filled_schedule = sum(frappe.utils.cstr(x.date) == cstr(date.date()) for x in post_filled_count)
			filled_post = sum(frappe.utils.cstr(x.date) == cstr(date.date()) for x in post_schedule_count)
			count = cstr(filled_schedule)+"/"+cstr(filled_post)
			highlight = "bggreen"
			if filled_schedule > filled_post:
				highlight = "bgyellow"  
			elif filled_schedule < filled_post:
				highlight = "bgred"
			post_list.append({'count': count, 'operations_role': key[0], 'date': cstr(date).split(" ")[0], 'highlight': highlight})

		post_count_data.update({key[0]: post_list })

	master_data.update({'operations_roles_data': post_count_data})
		
	end = time.time()
	print("[[[[[[]]]]]]]", end-start)
	return master_data

def filter_redundant_employees(employees):
	return list({employee['employee']:employee for employee in employees}.values())

@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, operations_role=None, active_posts=1, limit_start=0, limit_page_length=100):

	user, user_roles, user_employee = get_current_user_details()
	if "Operations Manager" not in user_roles and "Projects Manager" not in user_roles and "Site Supervisor" not in user_roles:
		frappe.throw(_("Insufficient permissions for Post View."))

	filters, master_data, post_data = {}, {}, {}
	if project:
		filters.update({'project': project})	
	if site:
		filters.update({'site': site})	
	if shift:
		filters.update({'site_shift': shift})	
	if operations_role:
		filters.update({'post_template': operations_role})	
	post_total = len(frappe.db.get_list("Operations Post", filters))
	post_list = frappe.db.get_list("Operations Post", filters, "name", order_by="name asc", limit_start=limit_start, limit_page_length=limit_page_length)
	fields = ['name', 'post', 'operations_role','date', 'post_status', 'site', 'shift', 'project']	

	filters.pop('post_template', None)
	filters.pop('site_shift', None)
	if operations_role:
		filters.update({'operations_role': operations_role})
	if shift:
		filters.update({'shift': shift})		
	for key, group in itertools.groupby(post_list, key=lambda x: (x['name'])):
		schedule_list = []
		filters.update({'date': ['between', (start_date, end_date)], 'post': key})
		schedules = frappe.db.get_list("Post Schedule", filters, fields, order_by="date asc, post asc")
		for date in	pd.date_range(start=start_date, end=end_date):
			if not any(cstr(schedule.date) == cstr(date).split(" ")[0] for schedule in schedules):
				schedule = {
				'post': key,
				'date': cstr(date).split(" ")[0]
				}
			else:
				schedule = next((sch for sch in schedules if cstr(sch.date) == cstr(date).split(" ")[0]), {}) 
			schedule_list.append(schedule)
		post_data.update({key: schedule_list})
	
	master_data.update({"post_data": post_data, "total": post_total})	
	return master_data

@frappe.whitelist()
def get_filtered_operations_roles(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	return frappe.db.sql("""
		select distinct post_template
		from `tabOperations Post` 
		where site_shift="{shift}"
	""".format(shift=shift))
	

def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
	return user, user_roles, user_employee

	
@frappe.whitelist()
def schedule_staff(employees, shift, operations_role, otRoster, start_date, project_end_date, keep_days_off, request_employee_schedule, day_off_ot=None, end_date=None):
	validation_logs = []
	user, user_roles, user_employee = get_current_user_details()

	if cint(project_end_date) and not end_date:
		project = frappe.db.get_value("Operations Shift", shift, ["project"])
		if frappe.db.exists("Contracts", {'project': project}):
			contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
			if not end_date:
				validation_logs.append("Please set contract end date for contract: {contract}".format(contract=contract))
		else:
			validation_logs.append("No contract linked with project {project}".format(project=project))
	
	elif end_date and not cint(project_end_date):
		end_date = end_date
	
	elif not cint(project_end_date) and not end_date:
		validation_logs.append("Please set an end date for scheduling the staff.")
	
	elif cint(project_end_date) and end_date:
		validation_logs.append("Please select either the project end date or set a custom date. You cannot set both!")

	emp_tuple = employees.replace('[', '(').replace(']',')')
	date_range = pd.date_range(start=start_date, end=end_date)

	if not cint(request_employee_schedule) and "Projects Manager" not in user_roles and "Operations Manager" not in user_roles:
		all_employee_shift_query = frappe.db.sql("""
			SELECT DISTINCT es.shift, s.supervisor
			FROM `tabEmployee Schedule` es JOIN `tabOperations Shift` s ON es.shift = s.name
			WHERE 
			es.date BETWEEN '{start_date}' AND '{end_date}'
			AND es.employee_availability='Working' AND es.employee IN {emp_tuple}
			GROUP BY es.shift
		""".format(start_date=start_date, end_date=end_date, emp_tuple=emp_tuple), as_dict=1)

		for i in all_employee_shift_query:
			if user_employee.name != i.supervisor:
				validation_logs.append("You are not authorized to change this schedule. Please check the Request Employee Schedule option to place a request.")
				break

	if len(validation_logs) > 0:
		frappe.throw(validation_logs)
		frappe.log_error(validation_logs)
	else:
		employees = json.loads(employees)
		frappe.enqueue(background_schedule_staff, employees=employees, start_date=start_date, end_date=end_date, shift=shift,
			operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off, day_off_ot=day_off_ot,
			request_employee_schedule=request_employee_schedule, is_async=True, now=False, queue='long')

		employees_list = frappe.db.sql(f"""
			SELECT name, employee_id, employee_name
			FROM `tabEmployee`
			WHERE name in {emp_tuple}
		""".format(emp_tuple=emp_tuple), as_dict=True)
		employee_dict = {}
		for i in employees_list:
			employee_dict[i.name] = i
		msgprint = "<span style='color:blue'>The following employees has been scheduled, if any errors, an email will be sent to {frappe.session.user} </span><br><br>".format(frappe=frappe)
		for i, j in enumerate(employees):
			msgprint += f"<i>{i+1}: {employee_dict[j].employee_id} - {employee_dict[j].employee_name} - {employee_dict[j].name}</i><hr>"

		frappe.msgprint(msgprint)
		# update_roster(key="roster_view")
	return True

def background_schedule_staff(employees, start_date, end_date, shift, operations_role, otRoster, keep_days_off, day_off_ot, request_employee_schedule):
	for employee in employees:
		frappe.publish_realtime(event='background_schedule_staff', message={'status':'success', 'message':f'Schedule started for {employee}'}, user=frappe.session.user)
		frappe.enqueue(queue_employee_schedule, employee=employee, start_date=start_date, end_date=end_date,
			shift=shift, operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off,
			day_off_ot=keep_days_off, request_employee_schedule=request_employee_schedule, is_async=True, now=False, queue='long')


def queue_employee_schedule(employee, start_date, end_date, shift, operations_role, otRoster, keep_days_off, day_off_ot, request_employee_schedule):
	try:
		if not cint(request_employee_schedule):
			schedule(employee=employee, start_date=start_date, end_date=end_date, shift=shift, operations_role=operations_role,
					 otRoster=otRoster, keep_days_off=keep_days_off, day_off_ot=day_off_ot)
			frappe.msgprint(f"Successfully started scheduling {employee}", alert=True)
		else:
			from_schedule = frappe.db.sql("""select shift, operations_role from `tabEmployee Schedule` where shift!= %(shift)s and date >= %(start_date)s and date <= %(end_date)s and employee = %(employee)s""",{
				'shift' : shift,
				'start_date': start_date,
				'end_date': end_date,
				'employee': employee
			}, as_dict=1)
			if len(from_schedule) > 0:
				from_shift = from_schedule[0].shift
				from_operations_role = from_schedule[0].operations_role
				create_request_employee_schedule(employee=employee, from_shift=from_shift, from_operations_role=from_operations_role,
												 to_shift=shift, to_operations_role=operations_role, otRoster=otRoster, start_date=start_date, end_date=end_date)
			# frappe.msgprint(f"Successfully created request for employee schedule for {employee}", alert=True)
			else:
				cannot_schedule.append(employee)
			# frappe.throw("This employee is not scheduled. Please uncheck Request Employee Schedule option.")
			# frappe.log_error("This employee is not scheduled. Please uncheck Request Employee Schedule option.", 'Roster Schedule')

	except Exception as e:
		frappe.log_error(e, 'Roster Schedule')
		notification = frappe.new_doc("Notification Log")
		notification.title = "Roster: {employee} not Scheduled".format(employee=employee)
		notification.subject = "Roster: {employee} not Scheduled".format(employee=employee)
		notification.email_content = "This employee is not scheduled. {str(e)}.<br>".format(e=e)
		notification.document_type = "Notification Log"
		notification.for_user = frappe.session.user
		notification.document_name = " "
		notification.category = 'Roster'
		notification.one_fm_mobile_app = 1
		notification.save(ignore_permissions=True)
		notification.document_name = notification.name
		notification.save(ignore_permissions=True)

def create_request_employee_schedule(employee, from_shift, from_operations_role, to_shift, to_operations_role, otRoster, start_date, end_date):
	if otRoster == 'false':
		roster_type = 'Basic'
	elif otRoster == 'true':
		roster_type = 'Over-Time'
	req_es_doc = frappe.new_doc("Request Employee Schedule")
	req_es_doc.employee = employee
	req_es_doc.from_shift = from_shift
	req_es_doc.from_operations_role = from_operations_role
	req_es_doc.to_shift = to_shift
	req_es_doc.to_operations_role = to_operations_role
	req_es_doc.start_date = start_date
	req_es_doc.end_date = end_date
	req_es_doc.roster_type = roster_type
	req_es_doc.save(ignore_permissions=True)
	frappe.db.commit()

	print("Created request for employee schedule")

def update_roster(key):
	frappe.publish_realtime(key, "Success")

def schedule(employee, shift, operations_role, otRoster, start_date, end_date, keep_days_off, day_off_ot):
	start = time.time()

	if otRoster == 'false':
		roster_type = 'Basic'
	elif otRoster == 'true':
		roster_type = 'Over-Time'

	emp_project, emp_site, emp_shift = frappe.db.get_value("Employee", employee, ["project", "site", "shift"])
			
	for date in	pd.date_range(start=start_date, end=end_date):
		if not cint(keep_days_off):
			if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date()), "roster_type" : roster_type}):
				site, project, shift_type= frappe.get_value("Operations Shift", shift, ["site", "project", "shift_type"])
				post_abbrv = frappe.get_value("Operations Role", operations_role, "post_abbrv")
				roster = frappe.get_value("Employee Schedule", {"employee": employee, "date": cstr(date.date()), "roster_type" : roster_type })
				update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, cstr(date.date()), "Working", operations_role, roster_type, day_off_ot)
			else:
				roster_doc = frappe.new_doc("Employee Schedule")
				roster_doc.employee = employee
				roster_doc.date = cstr(date.date())
				roster_doc.shift = shift
				roster_doc.employee_availability = "Working"
				roster_doc.operations_role = operations_role
				roster_doc.roster_type = roster_type
				roster_doc.day_off_ot = cint(day_off_ot)
				roster_doc.save(ignore_permissions=True)
		else:
			if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date()), "roster_type" : roster_type, 'employee_availability': 'Working'}):
				site, project, shift_type= frappe.get_value("Operations Shift", shift, ["site", "project", "shift_type"])
				post_abbrv = frappe.get_value("Operations Role", operations_role, "post_abbrv")
				roster = frappe.get_value("Employee Schedule", {"employee": employee, "date": cstr(date.date()), "roster_type" : roster_type })
				update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, cstr(date.date()), "Working", operations_role, roster_type, day_off_ot)
			elif not frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date()), "roster_type" : roster_type}):
				roster_doc = frappe.new_doc("Employee Schedule")
				roster_doc.employee = employee
				roster_doc.date = cstr(date.date())
				roster_doc.shift = shift
				roster_doc.employee_availability = "Working"
				roster_doc.operations_role = operations_role
				roster_doc.roster_type = roster_type
				roster_doc.day_off_ot = day_off_ot
				roster_doc.save(ignore_permissions=True)

	"""Update employee assignment"""
	site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])
	if emp_project and emp_project != project or emp_site and emp_site != site or emp_shift and emp_shift != shift:
		if frappe.db.exists("Additional Shift Assignment", {'employee': employee, 'project': project, 'site': site, 'shift': shift}):
			additional_shift_assignment_doc = frappe.get_doc("Additional Shift Assignment", {'employee': employee, 'project': project, 'site': site, 'shift': shift})
			additional_shift_assignment_doc.project = project
			additional_shift_assignment_doc.site = site
			additional_shift_assignment_doc.shift = shift
			additional_shift_assignment_doc.save(ignore_permissions=True)
		else:
			additional_shift_assignment_doc = frappe.new_doc("Additional Shift Assignment")
			additional_shift_assignment_doc.employee = employee
			additional_shift_assignment_doc.project = project
			additional_shift_assignment_doc.site = site
			additional_shift_assignment_doc.shift = shift
			additional_shift_assignment_doc.save(ignore_permissions=True)
	
	elif emp_project == project and emp_site == site and emp_shift == shift:
		frappe.db.sql(""" 
		DELETE FROM 
			`tabAdditional Shift Assignment`
		WHERE
			employee=%(employee)s
		""", {'employee': employee})

		# frappe.db.commit()

	elif emp_project and emp_site is None and emp_shift is None:
		update_employee_assignment(employee, project, site, shift)
	frappe.publish_realtime(event='background_schedule_staff',
							message={'status':'success', 'message':f"{employee} schedule between {start_date} and {end_date} is complete."}, user=frappe.session.user)

def update_employee_assignment(employee, project, site, shift):
	""" This function updates the employee project, site and shift in the employee doctype """
	frappe.db.set_value("Employee", employee, "project", val=project)
	frappe.db.set_value("Employee", employee, "site", val=site)
	frappe.db.set_value("Employee", employee, "shift", val=shift)
	

@frappe.whitelist()
def schedule_leave(employees, leave_type, start_date, end_date):
	try:
		for employee in json.loads(employees):
			for date in	pd.date_range(start=start_date, end=end_date):
				if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date": cstr(date.date())}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date": cstr(date.date())})
					roster.shift = None
					roster.shift_type = None
					roster.project = None
					roster.site = None
				else:
					roster = frappe.new_doc("Employee Schedule")
					roster.employee = employee["employee"]
					roster.date = cstr(date.date())
				roster.employee_availability = leave_type
				roster.save(ignore_permissions=True)
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist(allow_guest=True)
def unschedule_staff(employees, start_date, end_date=None, never_end=0):
	try:
		for employee in json.loads(employees):
			st = time.time()
			if cint(never_end) == 1:
				rosters = frappe.get_list("Employee Schedule", {"employee": employee["employee"],"date": ('>=', start_date)}, ignore_permissions=True)
				rosters = [roster.name for roster in rosters]
				rosters = ', '.join(['"{}"'.format(value) for value in rosters])
				if rosters:
					frappe.db.sql("""
						delete from `tabEmployee Schedule`
						where name in ({ids})
					""".format(ids=rosters))
			if end_date and cint(never_end) != 1:
				rosters = frappe.get_list("Employee Schedule", {"employee": employee["employee"], "date": ['between', (start_date, end_date)]}, ignore_permissions=True)
				rosters = [roster.name for roster in rosters]
				rosters = ', '.join(['"{}"'.format(value) for value in rosters])
				if rosters:
					frappe.db.sql("""
						delete from `tabEmployee Schedule`
						where name in ({ids})
					""".format(ids=rosters))
		frappe.db.commit()
		return True
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)

@frappe.whitelist()
def edit_post(posts, values):

	user, user_roles, user_employee = get_current_user_details()

	if "Operations Manager" not in user_roles and "Projects Manager" not in user_roles:
		frappe.throw(_("Insufficient permissions to Edit Post.")) 
	
	args = frappe._dict(json.loads(values))
	
	if args.post_status == "Plan Post":
		if args.plan_end_date and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))
	
		if not args.plan_end_date and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		frappe.enqueue(plan_post, posts=posts, args=args, is_async=True, queue='long')
	
	
	elif args.post_status == "Cancel Post":
		if args.cancel_end_date and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))
	
		if not args.cancel_end_date and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		frappe.enqueue(cancel_post,posts=posts, args=args, is_async=True, queue='long')
	
	
	elif args.post_status == "Suspend Post":
		if args.suspend_to_date and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))
	
		if not args.suspend_to_date and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		frappe.enqueue(suspend_post, posts=posts, args=args, is_async=True, queue='long')
	
	
	elif args.post_status == "Post Off":
		if args.repeat_till and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))
	
		if not args.repeat_till and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		if args.repeat == "Does not repeat" and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and choose 'Does not repeat' option!"))
		
		frappe.enqueue(post_off, posts=posts, args=args, is_async=True, queue='long')

	frappe.enqueue(update_roster, key="staff_view", is_async=True, queue='long')	
		
def plan_post(posts, args):
	""" This function sets the post status to planned provided a post, start date and an end date """

	end_date = None

	if args.plan_end_date and not cint(args.project_end_date):
		end_date = args.plan_end_date

	for post in json.loads(posts):
		if cint(args.project_end_date) and not args.plan_end_date:
			project = frappe.db.get_value("Operations Post", post["post"], ["project"])
			if frappe.db.exists("Contracts", {'project': project}):
				contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
				if not end_date:
					frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
			else:
				frappe.throw(_("No contract linked with project {project}".format(project=project)))	
		
		for date in pd.date_range(start=args.plan_from_date, end=end_date):
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post["post"]}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post["post"]})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post["post"]
				doc.date = cstr(date.date())
			doc.post_status = "Planned"
			doc.save()	
		frappe.db.commit()

def cancel_post(posts, args):
	end_date = None

	if args.cancel_end_date and not cint(args.project_end_date):
		end_date = args.plan_end_date

	for post in json.loads(posts):
		if cint(args.project_end_date) and not args.cancel_end_date:
			project = frappe.db.get_value("Operations Post", post["post"], ["project"])
			if frappe.db.exists("Contracts", {'project': project}):
				contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
				if not end_date:
					frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
			else:
				frappe.throw(_("No contract linked with project {project}".format(project=project)))	

		for date in	pd.date_range(start=args.cancel_from_date, end=end_date):
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post["post"]}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post["post"]})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post["post"]
				doc.date = cstr(date.date())	
			doc.paid = args.suspend_paid
			doc.unpaid = args.suspend_unpaid
			doc.post_status = "Cancelled"
			doc.save()
	frappe.db.commit()

def suspend_post(posts, args):
	end_date = None

	if args.suspend_to_date and not cint(args.project_end_date):
		end_date = args.suspend_to_date

	for post in json.loads(posts):
		if cint(args.project_end_date) and not args.suspend_to_date:
			project = frappe.db.get_value("Operations Post", post["post"], ["project"])
			if frappe.db.exists("Contracts", {'project': project}):
				contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
				if not end_date:
					frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
			else:
				frappe.throw(_("No contract linked with project {project}".format(project=project)))	

		for date in	pd.date_range(start=args.suspend_from_date, end=end_date):
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post["post"]}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post["post"]})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post["post"]
				doc.date = cstr(date.date())
			doc.paid = args.suspend_paid
			doc.unpaid = args.suspend_unpaid
			doc.post_status = "Suspended"
			doc.save()
	frappe.db.commit()

def post_off(posts, args):
	from one_fm.api.mobile.roster import month_range
	post_off_paid = args.post_off_paid
	post_off_unpaid = args.post_off_unpaid
	
	if args.repeat == "Does not repeat":
		for post in json.loads(posts):
			set_post_off(post["post"], post["date"], post_off_paid, post_off_unpaid)
	else:
		if args.repeat and args.repeat in ["Daily", "Weekly", "Monthly", "Yearly"]:
			end_date = None

			if args.repeat_till and not cint(args.project_end_date):
				end_date = args.repeat_till

			if args.repeat == "Daily":
				for post in json.loads(posts):
					if cint(args.project_end_date) and not args.repeat_till:
						project = frappe.db.get_value("Operations Post", post["post"], ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))	
					
					for date in	pd.date_range(start=post["date"], end=end_date):
						set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Weekly":
				week_days = []
				if args.sunday: week_days.append("Sunday")
				if args.monday: week_days.append("Monday")
				if args.tuesday: week_days.append("Tuesday")
				if args.wednesday: week_days.append("Wednesday")
				if args.thursday: week_days.append("Thursday")
				if args.friday: week_days.append("Friday")
				if args.saturday: week_days.append("Saturday")
				for post in json.loads(posts):
					if cint(args.project_end_date) and not args.repeat_till:
						project = frappe.db.get_value("Operations Post", post["post"], ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))	

					for date in	pd.date_range(start=post["date"], end=end_date):
						if getdate(date).strftime('%A') in week_days:
							set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Monthly":
				for post in json.loads(posts):
					if cint(args.project_end_date) and not args.repeat_till:
						project = frappe.db.get_value("Operations Post", post["post"], ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))	

					for date in	month_range(post["date"], end_date):
						set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Yearly":
				for post in json.loads(posts):
					if cint(args.project_end_date) and not args.repeat_till:
						project = frappe.db.get_value("Operations Post", post["post"], ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))
					
					for date in	pd.date_range(start=post["date"], end=end_date, freq=pd.DateOffset(years=1)):
						set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)
	frappe.db.commit()

def set_post_off(post, date, post_off_paid, post_off_unpaid):
	if frappe.db.exists("Post Schedule", {"date": date, "post": post}):
		doc = frappe.get_doc("Post Schedule", {"date": date, "post": post})
	else: 
		doc = frappe.new_doc("Post Schedule")
		doc.post = post
		doc.date = date
	doc.paid = post_off_paid
	doc.unpaid = post_off_unpaid
	doc.post_status = "Post Off"
	doc.save()
	


@frappe.whitelist()
def dayoff(employees, selected_dates=0, repeat=0, repeat_freq=None, week_days=[], repeat_till=None, project_end_date=None):
	
	if not repeat_till and not cint(project_end_date) and not selected_dates:
		frappe.throw(_("Please select either a repeat till date or check the project end date option."))

	from one_fm.api.mobile.roster import month_range
	if cint(selected_dates):
		for employee in json.loads(employees):
			set_dayoff(employee["employee"], employee["date"])
			frappe.msgprint(f"Successfully started scheduling day off for {employee}", alert=True)
	else:
		if repeat and repeat_freq in ["Daily", "Weekly", "Monthly", "Yearly"]:
			end_date = None
			if repeat_till and not cint(project_end_date):
				end_date = repeat_till

			if repeat_freq == "Daily":
				for employee in json.loads(employees):
					if cint(project_end_date):
						project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))	
					for date in	pd.date_range(start=employee["date"], end=end_date):
						frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')
						frappe.msgprint(f"Successfully started scheduling day off for {employee}", alert=True)

			elif repeat_freq == "Weekly":
				for employee in json.loads(employees):
					if cint(project_end_date):
						project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))	
					for date in	pd.date_range(start=employee["date"], end=end_date):
						if getdate(date).strftime('%A') in week_days:
							frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')
							frappe.msgprint(f"Successfully started scheduling day off for {employee}", alert=True)

			elif repeat_freq == "Monthly":
				for employee in json.loads(employees):
					if cint(project_end_date):
						project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))	
					for date in	month_range(employee["date"], end_date):
						frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')
						frappe.msgprint(f"Successfully started scheduling day off for {employee}", alert=True)

			elif repeat_freq == "Yearly":
				for employee in json.loads(employees):
					if cint(project_end_date):
						project = frappe.db.get_value("Employee", {'employee': employee["employee"]}, ["project"])
						if frappe.db.exists("Contracts", {'project': project}):
							contract, end_date = frappe.db.get_value("Contracts", {'project': project}, ["name", "end_date"])
							if not end_date:
								frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						else:
							frappe.throw(_("No contract linked with project {project}".format(project=project)))
					for date in	pd.date_range(start=employee["date"], end=end_date, freq=pd.DateOffset(years=1)):
						frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')
						frappe.msgprint(f"Successfully started scheduling day off for {employee}", alert=True)

def set_dayoff(employee, date):
	if frappe.db.exists("Employee Schedule", {"date": date, "employee": employee}):
		doc = frappe.get_doc("Employee Schedule", {"date": date, "employee": employee})

	else:
		doc = frappe.new_doc("Employee Schedule")

	doc.employee = employee
	doc.date = date
	doc.shift = None
	doc.operations_role = None
	doc.shift_type = None
	doc.site = None
	doc.project = None
	doc.employee_availability = "Day Off"
	doc.post_abbrv = None
	doc.roster_type = 'Basic'
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def assign_staff(employees, shift, request_employee_assignment):
	validation_logs = []
	user, user_roles, user_employee = get_current_user_details()
	if not cint(request_employee_assignment):
		for emp in json.loads(employees):
			emp_project, emp_site, emp_shift = frappe.db.get_value("Employee", emp, ["project", "site", "shift"])
			supervisor = frappe.db.get_value("Operations Shift", emp_shift, ["supervisor"])
			if user_employee.name != supervisor:
				validation_logs.append("You are not authorized to change assignment for employee {emp}. Please check the Request Employee Assignment option to place a request.".format(emp=emp))
		
	if len(validation_logs) > 0:
		frappe.throw(validation_logs)
		frappe.log_error(validation_logs)
	else:
		try:
			start = time.time()
			for employee in json.loads(employees):
				if not cint(request_employee_assignment):
					frappe.enqueue(assign_job, employee=employee, shift=shift, site=site, project=project, is_async=True, queue="long")
				else:
					emp_project, emp_site, emp_shift = frappe.db.get_value("Employee", employee, ["project", "site", "shift"])
					site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])
					if emp_project != project or emp_site != site or emp_shift != shift:
						frappe.enqueue(create_request_employee_assignment, employee=employee, from_shift=emp_shift, to_shift=shift, is_async=True, queue="long")
			frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long")
			end = time.time()
			print(end-start, "[TOTS]")
			return True

		except Exception as e:
			frappe.log_error(e)
			frappe.throw(_(e))

def create_request_employee_assignment(employee, from_shift, to_shift):
	req_ea_doc = frappe.new_doc("Request Employee Assignment")
	req_ea_doc.employee = employee
	req_ea_doc.from_shift = from_shift
	req_ea_doc.to_shift = to_shift
	req_ea_doc.save(ignore_permissions=True)


def assign_job(employee, shift, site, project):
	start = time.time()
	frappe.set_value("Employee", employee, "shift", shift)
	frappe.set_value("Employee", employee, "site", site)
	frappe.set_value("Employee", employee, "project", project)
	# for date in	pd.date_range(start=start_date, end=end_date):
	# 	if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
	# 		roster = frappe.get_value("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
	# 		update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, cstr(date.date()), "Working", operations_role)
	# 	else:
	# 		roster = frappe.new_doc("Employee Schedule")
	# 		roster.employee = employee
	# 		roster.date = cstr(date.date())
	# 		roster.shift = shift
	# 		roster.employee_availability = "Working"
	# 		roster.operations_role = operations_role
	# 		roster.save(ignore_permissions=True)
	end = time.time()
	print("------------------[TIME TAKEN]===================", end-start)

@frappe.whitelist(allow_guest=True)
def update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, date, employee_availability, operations_role, roster_type, day_off_ot):
	frappe.db.set_value("Employee Schedule", roster, "shift", val=shift)
	frappe.db.set_value("Employee Schedule", roster, "site", val=site)
	frappe.db.set_value("Employee Schedule", roster, "shift_type", val=shift_type)
	frappe.db.set_value("Employee Schedule", roster, "project", val=project)		
	frappe.db.set_value("Employee Schedule", roster, "post_abbrv", val=post_abbrv)
	frappe.db.set_value("Employee Schedule", roster, "date", val=date)
	frappe.db.set_value("Employee Schedule", roster, "employee_availability", val=employee_availability)
	frappe.db.set_value("Employee Schedule", roster, "operations_role", val=operations_role)
	frappe.db.set_value("Employee Schedule", roster, "roster_type", val=roster_type)
	frappe.db.set_value("Employee Schedule", roster, "day_off_ot", val=cint(day_off_ot))


@frappe.whitelist(allow_guest=True)
def search_staff(key, search_term):
	conds = ""
	if key == "customer" and search_term:
		conds += 'and prj.customer like "%{customer}%" and emp.project=prj.name'.format(customer=search_term)
	elif key == "employee_id" and search_term:
		conds += 'and emp.employee_id like "%{employee_id}%" '.format(employee_id=search_term)
	elif key == "project" and search_term:
		conds += 'and emp.project like "%{project}%" '.format(project=search_term)
	elif key == "site" and search_term:
		conds += 'and emp.site like "%{site}%" '.format(site=search_term)
	elif key == "employee_name" and search_term:
		conds += 'and emp.employee_name like "%{name}%" '.format(name=search_term)

	data = frappe.db.sql("""
		select 
			distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site, emp.project
		from `tabEmployee` as emp, `tabUser` as usr, `tabProject` as prj
		where 
		emp.user_id=usr.name
		{conds}
	""".format(conds=conds), as_dict=1)
	return data

@frappe.whitelist()
def get_employee_detail(employee_pk):
	if employee_pk:
		pk, employee_id, employee_name, enrolled, cell_number = frappe.db.get_value("Employee", employee_pk, ["name", "employee_id", "employee_name", "enrolled", "cell_number"])
		return {'pk':pk, 'employee_id': employee_id, 'employee_name': employee_name, 'enrolled': enrolled, "cell_number": cell_number}


@frappe.whitelist()
def check_realtime():
	frappe.log_error('Checking realtime', 'check_realtime')
	frappe.publish_progress(25, title='Some title', description='Some description')
	frappe.publish_realtime('test_1', {'key': 'value'})
	frappe.publish_realtime('msgprint', 'Starting long job...')
	frappe.publish_realtime('show_alert', 'hi you hVE...')
	frappe.publish_realtime(event='eval_js', message='alert("{0}")'.format(msg_var), user=frappe.session.user)
