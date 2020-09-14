import frappe
from frappe.utils import nowdate, add_to_date, cstr, cint, getdate
import itertools
import pandas as pd
import numpy as np
import time
from frappe import _
import json

@frappe.whitelist(allow_guest=True)
def get_staff(assigned=1, employee_id=None, employee_name=None, project=None, site=None, shift=None, department=None, designation=None):
	date = cstr(add_to_date(nowdate(), days=1))
	# date = "2020-07-05"
	conds = ""
	print(assigned, employee_id, employee_name, project, site, shift, department, designation)
	if not cint(assigned):
		data = frappe.db.sql("""
			select 
				distinct emp.name as employee_id, emp.employee_name, emp.image, emp.nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.project
			from `tabEmployee` as emp, `tabUser` as usr, `tabEmployee Schedule` as sch, `tabOperations Shift` as sh
			where 
				sch.date="{date}"
			and sch.employee<>emp.employee
			and emp.user_id=usr.name
			and sch.shift=sh.name
			and emp.project is NULL
		""".format(date=date, conds=conds), as_dict=1)
		return data

	if employee_name:
		conds += 'and emp.employee_name="{name}" '.format(name=employee_name)
	if project:
		conds += 'and sh.project="{project}" '.format(project=project)
	if site:
		conds += 'and sh.site="{site}" '.format(site=site)
	if shift:
		conds += 'and sh.name="{shift}" '.format(shift=shift)
	if department:
		conds += 'and emp.department="{department}" '.format(department=department)	
	if designation:
		conds += 'and emp.designation="{designation}" '.format(designation=designation)
	# print(conds)

	data = frappe.db.sql("""
		select 
			distinct emp.name as employee_id, emp.employee_name, emp.nationality, usr.mobile_no, usr.name as email, emp.designation, emp.department, sch.shift, sh.site, sh.project
		from `tabEmployee` as emp, `tabUser` as usr, `tabEmployee Schedule` as sch, `tabOperations Shift` as sh
		where 
			sch.date="{date}"
		and sch.employee=emp.employee
		and emp.user_id=usr.name
		and sch.shift=sh.name
		{conds}
	""".format(date=date, conds=conds), as_dict=1)
	print(data)
	return data

@frappe.whitelist(allow_guest=True)
def get_staff_filters_data():
	company = frappe.get_list("Company", limit_page_length=9999)
	projects = frappe.get_list("Project", limit_page_length=9999)
	sites = frappe.get_list("Operations Site", limit_page_length=9999)
	shifts = frappe.get_list("Operations Shift", limit_page_length=9999)
	departments = frappe.get_list("Department", limit_page_length=9999)
	designations = frappe.get_list("Designation", limit_page_length=9999)

	return {
		"company": company,
		"projects": projects,
		"sites": sites,
		"shifts": shifts,
		"departments": departments,
		"designations": designations
	}

@frappe.whitelist(allow_guest=True)
def get_roster_view(start_date, end_date, all=1, assigned=0, scheduled=0, project=None, site=None, shift=None, department=None, post_type=None):
	# Roster filters
	master_data = {}
	formatted_data = []
	formatted_employee_data = {}
	post_count_data = {}
	post_types_list = []
	filters = {
		'date': ['between', (start_date, end_date)]
	}
	if project:
		filters.update({'project': project})	
	if site:
		filters.update({'site': site})	
	if shift:
		filters.update({'shift': shift})	
	if department:
		filters.update({'department': department})	
	if post_type:
		filters.update({'post_type': post_type})	
	print(filters)
	fields = ["employee", "employee_name", "date", "post_type", "post_abbrv", "employee_availability", "shift"]
	
	if all:
		employee_filters = {}
		if project:
			employee_filters.update({'project': project})
		if department:
			employee_filters.update({'department': department})
		employees = frappe.get_list("Employee", employee_filters, ["employee", "employee_name"])
		post_types_list = frappe.get_list("Post Type", ["name", "post_abbrv"])

		for key, group in itertools.groupby(post_types_list, key=lambda x: (x['post_abbrv'], x['name'])):
			post_list = []
			for date in	pd.date_range(start=start_date, end=end_date):
				post_filters = {'date': cstr(date).split(" ")[0], 'post_type': key[1] }
				post_schedule_count = frappe.get_list("Post Schedule", post_filters)
				post_filled_count = frappe.get_list("Employee Schedule", post_filters)
				count = cstr(len(post_schedule_count))+"/"+cstr(len(post_filled_count))
				post_list.append({'count': count, 'post_type': key[0], 'date': cstr(date).split(" ")[0] })
			post_count_data.update({key[0]: post_list })
		master_data.update({'post_types_data': post_count_data})

		for key, group in itertools.groupby(employees, key=lambda x: (x['employee'], x['employee_name'])):
			schedule_list = []				
			for date in	pd.date_range(start=start_date, end=end_date):
				filters.update({'date': cstr(date).split(" ")[0], 'employee': key[0]})
				schedule = frappe.get_value("Employee Schedule", filters, fields, order_by="date asc, employee_name asc", as_dict=1)
				if not schedule:
					schedule = {
						'employee': key[0],
						'employee_name': key[1],
						'date': cstr(date).split(" ")[0]
					}
				schedule_list.append(schedule)
			formatted_employee_data.update({key[1]: schedule_list})
		master_data.update({'employees_data': formatted_employee_data})

	elif scheduled:
		data = frappe.get_list("Employee Schedule", filters, fields, order_by="date asc, employee_name asc")
		for key, group in itertools.groupby(data, key=lambda x: (x['post_type'],x['post_abbrv'])):
			print(key)
	elif not scheduled:
		pass
	elif assigned:
		pass
	elif not assigned:
		pass

	return master_data

@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, post_type=None, active_posts=1):
	filters = {}
	if project:
		filters.update({'project': project})	
	if site:
		filters.update({'site': site})	
	if shift:
		filters.update({'site_shift': shift})	
	if post_type:
		filters.update({'post_template': post_type})	

	post_list = frappe.get_list("Operations Post", filters, "name")
	print(post_list)
	fields = ['name', 'post', 'post_type','date', 'post_status', 'site', 'shift', 'project']	
	
	master_data = {}
	filters.pop('post_template', None)
	filters.pop('site_shift', None)
	if post_type:
		filters.update({'post_type': post_type})
	if shift:
		filters.update({'shift': shift})		
	for key, group in itertools.groupby(post_list, key=lambda x: (x['name'])):
		# filters.update({
			# 'date': ['between', (start_date, end_date)],
			# 'post_status': ['=', 'Planned'] if active_posts else ['in', ('Post Off', 'Suspended', 'Cancelled')]
		# })
		# data = frappe.get_list("Post Schedule", filters, fields, order_by="post asc, date asc")
		schedule_list = []
		for date in	pd.date_range(start=start_date, end=end_date):
			filters.update({'date': cstr(date).split(" ")[0], 'post': key})
			schedule = frappe.get_value("Post Schedule", filters, fields, order_by="post asc, date asc", as_dict=1)
			print(filters, schedule)
			print("----------------------------------------------------------------------------------------")
			print("----------------------------------------------------------------------------------------")
			if not schedule:
				schedule = {
					'post': key,
					'date': cstr(date).split(" ")[0]
				}
			schedule_list.append(schedule)
		master_data.update({key: schedule_list})
	
	print(master_data)

	return master_data

@frappe.whitelist()
def get_filtered_post_types(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get('shift')
	return frappe.db.sql("""
		select distinct post_template
		from `tabOperations Post` 
		where site_shift="{shift}"
	""".format(shift=shift))
	
@frappe.whitelist()
def schedule_staff(employees, shift, post_type):
	try:
		# print(employees, shift, site, post_type, project)
		for employee in json.loads(employees):
			print(getdate(employee["date"]).strftime('%A'))
			# print(employee["employee"], employee["date"])
			if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]}):
				roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]})
			else:
				roster = frappe.new_doc("Employee Schedule")
				roster.employee = employee["employee"]
				roster.date = employee["date"]
			roster.shift = shift
			roster.employee_availability = "Working"
			roster.post_type = post_type
			print(roster.as_dict())
			roster.save(ignore_permissions=True)
		return True
	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))

@frappe.whitelist()
def schedule_leave(employees, leave_type, start_date, end_date):
	try:
		for employee in json.loads(employees):
			for date in	pd.date_range(start=start_date, end=end_date):
				print(employee["employee"], date.date())
				if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date": employee["date"]})
					roster.shift = None
					roster.shift_type = None
					roster.project = None
					roster.site = None
				else:
					roster = frappe.new_doc("Employee Schedule")
					roster.employee = employee["employee"]
					roster.date = employee["date"]
				roster.employee_availability = leave_type
				roster.save(ignore_permissions=True)
	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)


@frappe.whitelist(allow_guest=True)
def unschedule_staff(employees, start_date, end_date=None, never_end=0):
	try:
		print(employees, start_date, never_end)
		for employee in json.loads(employees):
			if never_end:
				print(never_end, start_date)
				rosters = frappe.get_all("Employee Schedule", {"employee": employee["employee"],"date": ('>=', start_date)})
				for roster in rosters:
					frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)
			for date in	pd.date_range(start=start_date, end=end_date):
				print(employee["employee"], date.date())
				if frappe.db.exists("Employee Schedule", {"employee": employee["employee"], "date":  cstr(date.date())}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee["employee"], "date":  cstr(date.date())})
					frappe.delete_doc("Employee Schedule", roster.name, ignore_permissions=True)

	except Exception as e:
		print(e)
		return frappe.utils.response.report_error(e.http_status_code)