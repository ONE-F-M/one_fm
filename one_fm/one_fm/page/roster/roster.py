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

@frappe.whitelist(allow_guest=True)
def get_roster_view(start_date, end_date, all=1, assigned=0, scheduled=0, project=None, site=None, shift=None, department=None, post_type=None, limit_start=0, limit_page_length=100):
	start = time.time()
	master_data, formatted_employee_data, post_count_data, employee_filters={}, {}, {}, {}
	post_types_list = []

	filters = {
		'date': ['between', (start_date, end_date)]
	}

	if post_type:
		filters.update({'post_type': post_type})	
	fields = ["employee", "employee_name", "date", "post_type", "post_abbrv", "employee_availability", "shift"]

	if all:
		a1 = time.time()
		if project:
			employee_filters.update({'project': project})
		if site:
			employee_filters.update({'site': site})	
		if shift:
			employee_filters.update({'shift': shift})	
		if department:
			employee_filters.update({'department': department})
		

		roster_total = len(frappe.db.get_list("Employee", employee_filters))  
		master_data.update({'total': roster_total})

		employees = frappe.db.get_list("Employee", employee_filters, ["employee", "employee_name"], order_by="employee_name asc" ,limit_start=limit_start, limit_page_length=limit_page_length)

		a3 = time.time()
		print("A2", a3-a1)
		a4 = time.time()
		employee_filters.update({'date': ['between', (start_date, end_date)], 'post_status': 'Planned'})
		print(employee_filters)
		a5 = time.time()
		print("A3", a5-a4)

		if department:
			employee_filters.pop('department', None)
		if post_type:
			employee_filters.update({'post_type': post_type})

		post_types_list = frappe.db.get_list("Post Schedule", employee_filters, ["post_type", "post_abbrv"])
		if post_type:
			employee_filters.pop('post_type', None)
		employee_filters.pop('date')
		employee_filters.pop('post_status')
		a5 = time.time()
		print("A4", a5-a4)

		for key, group in itertools.groupby(employees, key=lambda x: (x['employee'], x['employee_name'])):
			filters.update({'date': ['between', (start_date, end_date)], 'employee': key[0]})
			schedules = frappe.db.get_list("Employee Schedule", filters, fields, order_by="date asc, employee_name asc")
			schedule_list = []
			schedule = {}
			for date in	pd.date_range(start=start_date, end=end_date):
				if not any(cstr(schedule.date) == cstr(date).split(" ")[0] for schedule in schedules):
					schedule = {
						'employee': key[0],
						'employee_name': key[1],
						'date': cstr(date).split(" ")[0]
					}
				else:
					schedule = next((sch for sch in schedules if cstr(sch.date) == cstr(date).split(" ")[0]), {}) 
				schedule_list.append(schedule)
			formatted_employee_data.update({key[1]: schedule_list})

		master_data.update({'employees_data': formatted_employee_data})
		a6 = time.time()
		print("A5", a6-a5)

		for key, group in itertools.groupby(post_types_list, key=lambda x: (x['post_abbrv'], x['post_type'])):
			post_list = []
			post_filters = employee_filters
			post_filters.update({'date':  ['between', (start_date, end_date)], 'post_type': key[1]})
			post_filled_count = frappe.db.get_list("Employee Schedule",["name", "employee", "date"] ,{'date':  ['between', (start_date, end_date)],'post_type': key[1] }, order_by="date asc")
			post_filters.update({"post_status": "Planned"})
			post_schedule_count = frappe.db.get_list("Post Schedule", ["name", "date"], post_filters)
			post_filters.pop("post_status", None)
			c1 = time.time()

			for date in	pd.date_range(start=start_date, end=end_date):
				filled_schedule = sum(frappe.utils.cstr(x.date) == cstr(date.date()) for x in post_filled_count)
				filled_post = sum(frappe.utils.cstr(x.date) == cstr(date.date()) for x in post_schedule_count)
				# post_filters = employee_filters
				# post_filters.update({'date': cstr(date).split(" ")[0], 'post_type': key[1]})
				# print("[POST FILTERS]", post_filters)

				# post_filled_count = frappe.db.get_list("Employee Schedule", post_filters)

				# post_filters.update({"post_status": "Planned"})
				# post_schedule_count = frappe.db.get_list("Post Schedule", post_filters)
				# post_filters.pop("post_status", None)

				# count = cstr(len(post_schedule_count))+"/"+cstr(len(post_filled_count))
				count = cstr(filled_post)+"/"+cstr(filled_schedule)
				post_list.append({'count': count, 'post_type': key[0], 'date': cstr(date).split(" ")[0] })

			post_count_data.update({key[0]: post_list })
			c2 = time.time()
			# print("C", c2-c1)

		master_data.update({'post_types_data': post_count_data})
		a7 = time.time()
		print("A7", a7-a6)
		

	end = time.time()
	print("[[[[[[]]]]]]]", end-start)
	return master_data

@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, post_type=None, active_posts=1, limit_start=0, limit_page_length=100):
	a1 = time.time()
	filters = {}
	if project:
		filters.update({'project': project})	
	if site:
		filters.update({'site': site})	
	if shift:
		filters.update({'site_shift': shift})	
	if post_type:
		filters.update({'post_template': post_type})	
	post_total = len(frappe.get_list("Operations Post", filters))
	post_list = frappe.get_list("Operations Post", filters, "name", order_by="name asc", limit_start=limit_start, limit_page_length=limit_page_length)
	fields = ['name', 'post', 'post_type','date', 'post_status', 'site', 'shift', 'project']	
	a2 = time.time()
	print("A", a2-a1)
	a1 = time.time()
	master_data = {}
	post_data = {}
	filters.pop('post_template', None)
	filters.pop('site_shift', None)
	if post_type:
		filters.update({'post_type': post_type})
	if shift:
		filters.update({'shift': shift})		
	for key, group in itertools.groupby(post_list, key=lambda x: (x['name'])):
		schedule_list = []
		filters.update({'date': ['between', (start_date, end_date)], 'post': key})
		schedules = frappe.db.get_list("Post Schedule", filters, fields, order_by="date asc, post asc")
		print(schedules, key)
		for date in	pd.date_range(start=start_date, end=end_date):
			if not any(cstr(schedule.date) == cstr(date).split(" ")[0] for schedule in schedules):
				schedule = {
				'post': key,
				'date': cstr(date).split(" ")[0]
				}
			else:
				schedule = next((sch for sch in schedules if cstr(sch.date) == cstr(date).split(" ")[0]), {}) 
			schedule_list.append(schedule)


			# filters.update({'date': cstr(date).split(" ")[0], 'post': key})
			# schedule = frappe.get_value("Post Schedule", filters, fields, order_by="post asc, date asc", as_dict=1)
			# if not schedule:
			# 	schedule = {
			# 		'post': key,
			# 		'date': cstr(date).split(" ")[0]
			# 	}
			# schedule_list.append(schedule)
		print(schedule_list)
		post_data.update({key: schedule_list})
	
	master_data.update({"post_data": post_data, "total": post_total})	
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
def schedule_staff(employees, shift, post_type, start_date, end_date):
	import time
	try:
		start = time.time()
		for employee in json.loads(employees):
			frappe.enqueue(schedule, employee=employee, start_date=start_date, end_date=end_date, shift=shift, post_type=post_type, is_async=True, queue='long')
		frappe.enqueue(update_roster, key="roster_view", is_async=True, queue='long')
		
		end = time.time()
		print("[TOTAL]", end-start)
		return True
	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))

def update_roster(key):
	frappe.publish_realtime(key, "Success")

def schedule(employee, shift, post_type, start_date, end_date):
	start = time.time()
	for date in	pd.date_range(start=start_date, end=end_date):
		if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
			site, project, shift_type = frappe.get_value("Operations Shift", shift, ["site", "project", "shift_type"])
			post_abbrv = frappe.get_value("Post Type", post_type, "post_abbrv")
			roster = frappe.get_value("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
			update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, cstr(date.date()), "Working", post_type)
		else:
			roster = frappe.new_doc("Employee Schedule")
			roster.employee = employee
			roster.date = cstr(date.date())
			roster.shift = shift
			roster.employee_availability = "Working"
			roster.post_type = post_type
			roster.save(ignore_permissions=True)
	end = time.time()
	print(employee, end-start)

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
				rosters = frappe.get_list("Employee Schedule", {"employee": employee["employee"],"date": ('>=', start_date)})
				rosters = [roster.name for roster in rosters]
				rosters = ', '.join(['"{}"'.format(value) for value in rosters])
				if rosters:
					frappe.db.sql("""
						delete from `tabEmployee Schedule`
						where name in ({ids})
					""".format(ids=rosters))
			if end_date and cint(never_end) != 1:
				rosters = frappe.get_list("Employee Schedule", {"employee": employee["employee"], "date": ['between', (start_date, end_date)]})
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
	args = frappe._dict(json.loads(values))
	if args.post_status == "Cancel Post":
		cancel_post(posts, args)
	elif args.post_status == "Suspend Post":
		suspend_post(posts, args)
	elif args.post_status == "Post Off":
		post_off(posts, args)
	

def cancel_post(posts, args):
	for post in json.loads(posts):
		project = frappe.get_value("Operations Post", post, "project")
		end_date = frappe.get_value("Contracts", {"project": project}, "end_date")

		for date in	pd.date_range(start=args.cancel_from_date, end=end_date):
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post
				doc.date = cstr(date.date())	
			doc.paid = args.suspend_paid
			doc.unpaid = args.suspend_unpaid
			doc.post_status = "Cancelled"
			doc.save()
	frappe.db.commit()

def suspend_post(posts, args):
	for post in json.loads(posts):
		for date in	pd.date_range(start=args.suspend_from_date, end=args.suspend_to_date):

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
			end_date = args.repeat_till

			if args.repeat == "Daily":
				for post in json.loads(posts):
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
					for date in	pd.date_range(start=post["date"], end=end_date):
						if getdate(date).strftime('%A') in week_days:
							set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Monthly":
				for post in json.loads(posts):
					for date in	month_range(post["date"], args.repeat_till):
						set_post_off(post["post"], cstr(date.date()), post_off_paid, post_off_unpaid)

			elif args.repeat == "Yearly":
				for date in	pd.date_range(start=post["date"], end=args.repeat_till, freq=pd.DateOffset(years=1)):
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
def dayoff(employees, selected_dates=0, repeat=0, repeat_freq=None, week_days=[], repeat_till=None):
	from one_fm.api.mobile.roster import month_range
	print(selected_dates, type(selected_dates))
	if cint(selected_dates):
		for employee in json.loads(employees):
			set_dayoff(employee["employee"], employee["date"])
	else:
		if repeat and repeat_freq in ["Daily", "Weekly", "Monthly", "Yearly"]:
			end_date = repeat_till

			if repeat_freq == "Daily":
				for employee in json.loads(employees):
					for date in	pd.date_range(start=employee["date"], end=end_date):
						frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')

			elif repeat_freq == "Weekly":
				for employee in json.loads(employees):
					for date in	pd.date_range(start=employee["date"], end=end_date):
						if getdate(date).strftime('%A') in week_days:
							frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')

			elif repeat_freq == "Monthly":
				for employee in json.loads(employees):
					for date in	month_range(employee["date"], repeat_till):
						frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')

			elif repeat_freq == "Yearly":
				for date in	pd.date_range(start=employee["date"], end=repeat_till, freq=pd.DateOffset(years=1)):
					frappe.enqueue(set_dayoff, employee=employee["employee"], date=cstr(date.date()), queue='short')

def set_dayoff(employee, date):
	if frappe.db.exists("Employee Schedule", {"date": date, "employee": employee}):
		doc = frappe.get_doc("Employee Schedule", {"date": date, "employee": employee})

	else:
		doc = frappe.new_doc("Employee Schedule")

	doc.employee = employee
	doc.date = date
	doc.shift = None
	doc.post_type = None
	doc.shift_type = None
	doc.site = None
	doc.project = None
	doc.employee_availability = "Day Off"
	doc.post_abbrv = None
	doc.save()


@frappe.whitelist()
def assign_staff(employees, shift, post_type, assign_from, assign_date, assign_till_date):
	try:
		if assign_from == 'Immediately':
			assign_date = cstr(add_to_date(nowdate(), days=1))

		start = time.time()
		for employee in json.loads(employees):
			frappe.enqueue(assign_job, employee=employee, start_date=assign_date, end_date=assign_till_date, shift=shift, post_type=post_type, is_async=True, queue="long")
		frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long")
		end = time.time()
		print(end-start, "[TOTS]")
		return True

	except Exception as e:
		frappe.log_error(e)
		frappe.throw(_(e))

def assign_job(employee, start_date, end_date, shift, post_type):
	start = time.time()
	site, project, shift_type = frappe.get_value("Operations Shift", shift, ["site", "project", "shift_type"])
	post_abbrv = frappe.get_value("Post Type", post_type, "post_abbrv")
	frappe.set_value("Employee", employee, "shift", shift)
	frappe.set_value("Employee", employee, "site", site)
	frappe.set_value("Employee", employee, "project", project)
	for date in	pd.date_range(start=start_date, end=end_date):
		if frappe.db.exists("Employee Schedule", {"employee": employee, "date": cstr(date.date())}):
			roster = frappe.get_value("Employee Schedule", {"employee": employee, "date": cstr(date.date())})
			update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, cstr(date.date()), "Working", post_type)
		else:
			roster = frappe.new_doc("Employee Schedule")
			roster.employee = employee
			roster.date = cstr(date.date())
			roster.shift = shift
			roster.employee_availability = "Working"
			roster.post_type = post_type
			roster.save(ignore_permissions=True)
	end = time.time()
	print("------------------[TIME TAKEN]===================", end-start)


def update_existing_schedule(roster, shift, site, shift_type, project, post_abbrv, date, employee_availability, post_type):
	frappe.db.set_value("Employee Schedule", roster, "shift", val=shift)
	frappe.db.set_value("Employee Schedule", roster, "site", val=site)
	frappe.db.set_value("Employee Schedule", roster, "shift_type", val=shift_type)
	frappe.db.set_value("Employee Schedule", roster, "project", val=project)		
	frappe.db.set_value("Employee Schedule", roster, "post_abbrv", val=post_abbrv)
	frappe.db.set_value("Employee Schedule", roster, "date", val=date)
	frappe.db.set_value("Employee Schedule", roster, "employee_availability", val=employee_availability)
	frappe.db.set_value("Employee Schedule", roster, "post_type", val=post_type)


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