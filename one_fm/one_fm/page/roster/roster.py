import pandas as pd
import json
from distutils.util import strtobool
from collections import defaultdict
from pandas.core.indexes.datetimes import date_range
from datetime import datetime
from functools import reduce
from operator import and_

import frappe
from frappe import _
from frappe.utils import (
	nowdate, add_to_date, cstr, cint, getdate, now, today, add_days, add_months,
	get_first_day, get_last_day, date_diff, get_last_day
)
from frappe.query_builder import DocType, Order

from one_fm.one_fm.page.roster.employee_map  import CreateMap, PostMap
from one_fm.api.v1.utils import response



@frappe.whitelist(allow_guest=True)
def get_staff(assigned=1, employee_id=None, employee_name=None, company=None, project=None, site=None, shift=None, department=None, designation=None):
	date = cstr(add_to_date(nowdate(), days=1))
	conds = "and shift_working = 1 "

	if employee_name:
		conds += "and emp.employee_name='{name}' ".format(name=employee_name)
	if department:
		conds += "and emp.department='{department}' ".format(department=department)
	if designation:
		conds += "and emp.designation='{designation}' ".format(designation=designation)
	if company:
		conds += "and emp.company='{company}' ".format(company=company)

	if project:
		conds += "and emp.project='{project}' ".format(project=project)
	if site:
		conds += "and emp.site='{site}' ".format(site=site)
	if shift:
		conds += "and emp.name='{shift}' ".format(shift=shift)

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
			distinct emp.name, emp.employee_id, emp.employee_name, emp.image, emp.one_fm_nationality as nationality,
		   usr.mobile_no, usr.name as email, emp.designation, emp.department, emp.shift, emp.site,
		 emp.project,opsite.account_supervisor_name as site_supervisor,opshift.supervisor_name as shift_supervisor, emp.custom_operations_role_allocation, emp.custom_is_reliever
		from `tabEmployee` as emp, `tabUser` as usr,`tabOperations Shift` as opshift,`tabOperations Site` as opsite
		where
		emp.project is not NULL
		and emp.site is not NULL
		and emp.shift is not NULL
		and emp.user_id=usr.name
		and emp.shift = opshift.name
		and emp.site = opsite.name
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


def build_employee_filters(Employee, start_date, end_date, employee_search_id, employee_search_name, project, site, shift, department, is_reliever, operations_role, designation):
	filter_params = []
	filter_params.append((Employee.status.isin(["Active", "Vacation"]) | ((Employee.status == "Left") &  (Employee.relieving_date.between(start_date, end_date))))) 
	filter_params.append(Employee.shift_working == 1)
	filter_params.append(Employee.attendance_by_timesheet == 0)

	if employee_search_id: filter_params.append(Employee.employee_id == employee_search_id),
	if employee_search_name: filter_params.append(Employee.employee_name.like(f"%{employee_search_name}%" if employee_search_name else None)),
	if is_reliever: filter_params.append(Employee.custom_is_reliever == strtobool(is_reliever) if is_reliever else 0),
	if project: filter_params.append(Employee.project == project),
	if site: filter_params.append(Employee.site == site),
	if shift: filter_params.append(Employee.shift == shift),
	if department: filter_params.append(Employee.department == department),
	if operations_role: filter_params.append(Employee.custom_operations_role_allocation == operations_role),
	if designation: filter_params.append(Employee.designation == designation)

	return combine_filters(filter_params)


def build_employee_schedule_filters(EmployeeSchedule, start_date, end_date, employee_search_name, project, site, shift, department, operations_role):
	filter_params = []

	if start_date and end_date: filter_params.append(EmployeeSchedule.date.between(start_date, end_date)),
	if employee_search_name: filter_params.append(EmployeeSchedule.employee_name.like(f"%{employee_search_name}%" if employee_search_name else None)),
	if project: filter_params.append(EmployeeSchedule.project == project),
	if site: filter_params.append(EmployeeSchedule.site == site),
	if shift: filter_params.append(EmployeeSchedule.shift == shift),
	if department: filter_params.append(EmployeeSchedule.department == department),
	if operations_role: filter_params.append(EmployeeSchedule.operations_role == operations_role),

	return combine_filters(filter_params)

def get_post_schedule_filters(start_date, end_date, project, site, shift, operations_role):
	# Define all possible filters and their values
	filter_params = {
		"date": ["between", (start_date, end_date)],
		"project": project,
		"site": site,
		"shift": shift,
		"operations_role": operations_role,
	}

	# Build the dictionary with only the keys that have a value
	post_schedule_filters = {k: v for k, v in filter_params.items() if v is not None and v !=""}
	return post_schedule_filters


# Combine filters using reduce and and_ (only if filters are present)
def combine_filters(filters):
	return reduce(and_, filters) if filters else None


def get_employees_for_roster_view(start_date, end_date, employee_search_id=None, employee_search_name=None,
	project=None, site=None, shift=None, department=None, operations_role=None, designation=None,
	reliever=False):
	try:
		Employee = DocType("Employee")
		employee_filters = build_employee_filters(Employee, start_date, end_date, employee_search_id, employee_search_name, project, site, shift, department, reliever, operations_role, designation)

		# Employee query
		employee_query = (
			frappe.qb
			.from_(Employee)
			.select(Employee.name, Employee.employee_name)
		)

		if employee_filters:
			employee_query = employee_query.where(employee_filters)
		
		if reliever or employee_search_id or employee_search_name or designation or department:
			employees = frappe.db.sql(employee_query, as_dict=True)
			return employees

		EmployeeSchedule = DocType("Employee Schedule")
		employee_schedule_filters = build_employee_schedule_filters(EmployeeSchedule, start_date, end_date, employee_search_name, project, site, shift, department, operations_role)

		# Employee Schedule query (get employee field as name)
		schedule_query = (
			frappe.qb
			.from_(EmployeeSchedule)
			.select(EmployeeSchedule.employee.as_("name"), EmployeeSchedule.employee_name)
		)
		if employee_schedule_filters:
			schedule_query = schedule_query.where(employee_schedule_filters)

		# Combine both queries using UNION (no need for .distinct(), UNION removes duplicates)
		# combined_query = employee_query.union(schedule_query).orderby("employee_name", order=Order.asc)
        
		combined_query = (
            frappe.qb
            .from_(
                employee_query.union_all(schedule_query).as_("combined")
            )
            .select("name", "employee_name")
            .distinct()
            .orderby("employee_name", order=Order.asc)
        )
		# Execute the query
		employees = frappe.db.sql(combined_query, as_dict=True)
		return employees
	except Exception as e:
		frappe.log_error("Employees for Roster View", frappe.get_traceback())
		

@frappe.whitelist()
def get_roster_view(start_date, end_date, employee_search_id=None, employee_search_name=None,
	project=None, site=None, shift=None, department=None, operations_role=None, designation=None,
	reliever=False, limit_start=0, limit_page_length=9999):
	try:
		limit_start = cint(limit_start)
		limit_page_length = cint(limit_page_length)
		master_data = {}
		employees = get_employees_for_roster_view(start_date, end_date, employee_search_id, employee_search_name, project, 
			site, shift, department, operations_role, designation, reliever)
		master_data["total"] = len(employees)
		employees = employees[limit_start:limit_start + limit_page_length]

		# The following section creates a iterable that uses the employee name and id as keys and groups  the  employee data fetched in previous queries
		new_map=CreateMap(start=start_date, end=end_date, employees=employees, operations_role=operations_role)
		master_data["employees_data"] = new_map.formated_rs


		#----------------- Get Operations Role count and check fill status -------------------#
		post_schedule_filters = get_post_schedule_filters(start_date, end_date, project, site, shift, operations_role)
		operations_roles = frappe.get_all("Post Schedule", post_schedule_filters, ["distinct operations_role", "post_abbrv"])
		post_map_filters = {}
		if project:
			post_map_filters["project"] = project
		if site:
			post_map_filters["site"] = site
		if shift:
			post_map_filters["shift"] = shift
		post_map = PostMap(start=start_date, end=end_date, operations_roles_list=operations_roles, filters=post_map_filters)
		master_data["operations_roles_data"] = post_map.template

		response("Success", 200, master_data)
	except Exception as e:
		return response("Server Error", 500, None, str(frappe.get_traceback()))


@frappe.whitelist(allow_guest=True)
def get_post_view(start_date, end_date,  project=None, site=None, shift=None, operations_role=None, active_posts=1, limit_start=0, limit_page_length=100):

	user, user_roles, user_employee = get_current_user_details()
	if "Operations Manager" not in user_roles and "Projects Manager" not in user_roles and "Site Supervisor" not in user_roles:
		frappe.throw(_("Insufficient permissions for Post View."))

	filters, master_data, post_data = {}, {}, {}
	if project:
		filters.update({"project": project})
	if site:
		filters.update({"site": site})
	if shift:
		filters.update({"site_shift": shift})
	if operations_role:
		filters.update({"post_template": operations_role})

	post_total = frappe.db.count("Operations Post", filters)

	post_filters = dict(filters)
	post_filters.update(dict(status="Active"))

	post_list = frappe.db.get_list("Operations Post", post_filters, "name", order_by="name asc", limit_start=limit_start, limit_page_length=limit_page_length)
	fields = ["name", "post", "operations_role","date", "post_status", "site", "shift", "project"]

	filters.pop("post_template", None)
	filters.pop("site_shift", None)

	if operations_role:
		filters["operations_role"] = operations_role
	if shift:
		filters["shift"] = shift

	post_names = [p["name"] for p in post_list]
	if not post_names:
		master_data.update({"post_data": {}, "total": post_total})
		return master_data

	filters["date"] = ["between", (start_date, end_date)]
	filters["post"] = ["in", post_names]

	# Fetch all schedules for all posts in one query
	all_schedules = frappe.db.get_list(
		"Post Schedule",
		filters,
		fields,
		order_by="date asc, post asc"
	)


	schedule_lookup = defaultdict(dict)
	for sch in all_schedules:
		# Use string date for consistent comparison
		schedule_lookup[sch["post"]][str(sch["date"])] = sch

	# Precompute date range as strings
	date_range_pd = pd.date_range(start=start_date, end=end_date)
	date_range_str = [str(d.date()) for d in date_range_pd]


	for post in post_list:
		key = post["name"]
		schedule_list = []
		for date_str_iter in date_range_str:
			schedule = schedule_lookup[key].get(date_str_iter)
			if not schedule:
				schedule = {
					"post": key,
					"date": date_str_iter
				}
			schedule_list.append(schedule)
		post_data[key] = schedule_list

	master_data.update({"post_data": post_data, "total": post_total})
	return master_data


@frappe.whitelist()
def get_filtered_operations_role(doctype, txt, searchfield, start, page_len, filters):
	shift = filters.get("shift")
	return frappe.db.sql("""
		select distinct name
		from `tabOperations Role`
		where shift="{shift}" AND status = "Active"
	""".format(shift=shift))


def get_current_user_details():
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	user_employee = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_id", "employee_name", "image", "enrolled", "designation"], as_dict=1)
	return user, user_roles, user_employee


def get_employee_leave_attendance(employees,start_date):
	"""Returns a dict of employees and their corresponding attendance dates if it falls on or after the start date

	Args:
		employees (list): list of employees

	Returns:
		dict: list of dictionaries
	"""
	attendance_dict = {}
	all_attendance = frappe.get_all("Attendance", {"attendance_date": [">=", start_date ], "employee": ["IN",employees], "docstatus": 1, "status": "On Leave" }, ["attendance_date","employee"])
	if all_attendance:
		for each in all_attendance:
			if attendance_dict.get(each.employee):
				attendance_dict[each.employee].append(each.attendance_date)
			else:
				attendance_dict[each.employee] = [each.attendance_date]
	return attendance_dict

@frappe.whitelist()
def schedule_overtime(employees, shift, operations_role):
	try:
		employees = json.loads(employees)
		if not employees:
			frappe.throw("Employees must be selected.")

		employee_list = list({obj["employee"] for obj in employees})

		# extreme schedule
		extreme_schedule(employees=employees, start_date=today(), end_date=None, shift=shift,
			operations_role=operations_role, otRoster="true", keep_days_off=0, day_off_ot=0,
			request_employee_schedule=0, employee_list=employee_list
		)
		update_roster(key="roster_view")

		response("success", 200, {"message":"Successfully scheduled overtime for employees"})
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Schedule Overtime")
		response("error", 200, None, str(e))


@frappe.whitelist()
def schedule_staff(employees, shift, operations_role, otRoster, start_date, project_end_date, keep_days_off=0, request_employee_schedule=0, day_off_ot=None, end_date=None, selected_days_only=0):
	try:
		_start_date = getdate(start_date)

		validation_logs = []
		user, user_roles, user_employee = get_current_user_details()

		employees = json.loads(employees)
		if not employees:
			frappe.throw("Employees must be selected.")

		employee_list = list({obj["employee"] for obj in employees})
		employee_leave_attendance = get_employee_leave_attendance(employee_list,start_date)
		if cint(project_end_date) and not end_date:
			project = frappe.db.get_value("Operations Shift", shift, ["project"])
			if frappe.db.exists("Contracts", {"project": project}):
				contract, end_date_val = frappe.db.get_value("Contracts", {"project": project}, ["name", "end_date"])
				if not end_date_val:
					validation_logs.append("Please set contract end date for contract: {contract}".format(contract=contract))
				else:
					end_date = end_date_val
					employees = []
					list_of_date = date_range(start_date, end_date)
					for obj in employee_list:
						for day in list_of_date:
							if  day.date() not in employee_leave_attendance.get(obj,[]):
								employees.append({"employee": obj, "date": str(day.date())})

			else:
				validation_logs.append("No contract linked with project {project}".format(project=project))

		elif end_date and not cint(project_end_date):
			end_date_val = getdate(end_date)
			employees = []
			list_of_date = date_range(start_date, end_date_val)
			for obj in employee_list:
				for day in list_of_date:
					if  day.date() not in employee_leave_attendance.get(obj,[]):
						employees.append({"employee": obj, "date": str(day.date())})
			end_date = end_date_val

		elif not cint(project_end_date) and not end_date and not selected_days_only:
			validation_logs.append("Please set an end date for scheduling the staff.")

		elif cint(project_end_date) and end_date:
			validation_logs.append("Please select either the project end date or set a custom date. You cannot set both!")

		emp_tuple = str(employee_list).replace("[", "(").replace("]",")")

		if not cint(request_employee_schedule) and "Projects Manager" not in user_roles and "Operations Manager" not in user_roles:
			all_employee_shift_query = frappe.db.sql("""
				SELECT DISTINCT es.shift, s.supervisor
				FROM `tabEmployee Schedule` es JOIN `tabOperations Shift` s ON es.shift = s.name
				WHERE
				es.date BETWEEN "{start_date}" AND "{end_date}"
				AND es.employee_availability="Working" AND es.employee IN {emp_tuple}
				GROUP BY es.shift
			""".format(start_date=start_date, end_date=end_date, emp_tuple=emp_tuple), as_dict=1)

		if len(validation_logs) > 0:
			frappe.log_error(str(validation_logs), "Roster Schedule")
			frappe.throw(str(validation_logs))
		else:
			# extreme schedule
			extreme_schedule(employees=employees, start_date=start_date, end_date=end_date, shift=shift,
				operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off, day_off_ot=day_off_ot,
				request_employee_schedule=request_employee_schedule, employee_list=employee_list
			)
			update_roster(key="roster_view")


			response("success", 200, {"message":"Successfully rostered employees"})
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Schedule Roster")
		response("error", 200, None, str(e))

def update_roster(key):
	frappe.publish_realtime(key, "Success")


def extreme_schedule(employees, shift, operations_role, otRoster, start_date, end_date, keep_days_off, day_off_ot,
	request_employee_schedule, employee_list, selected_reliever=None):
	if not employees:
		frappe.throw("Please select employees before rostering")
		return
	creation = now()
	owner = frappe.session.user
	operations_shift_doc = frappe.get_doc("Operations Shift", shift, ignore_permissions=True)
	operations_role_doc = frappe.get_doc("Operations Role", operations_role, ignore_permissions=True)
	day_off_ot = cint(day_off_ot)
	if otRoster == "false":
		roster_type = "Basic"
	elif otRoster == "true" or day_off_ot == 1:
		roster_type = "Over-Time"

	# check for end date
	if end_date:
		end_date_val = getdate(end_date)
		new_employees = []
		for i in employees:
			if getdate(i["date"]) <= end_date_val:
				new_employees.append(i)
		if new_employees:
			employees = new_employees.copy()

	# check keep days_off
	if cint(keep_days_off):
		days_off_list = frappe.db.get_list("Employee Schedule", filters={
			"employee":["IN", [i["employee"] for i in employees]],
			"date": ["IN", [i["date"] for i in employees]],
			"employee_availability": "Day Off"
		}, fields=["name", "employee", "date"])
		days_off_dict = {}
		if days_off_list:
			# build a dict in the form {"hr-emp-0002:["2023-01-01,]}
			for i in days_off_list:
				if days_off_dict.get(i.employee):
					days_off_dict[i.employee].append(str(i.date))
				else:
					days_off_dict[i.employee] = [str(i.date)]
			new_employees = []
			if employees and len(days_off_dict):
				for i in employees:
					if not (i.get("date") in days_off_dict.get(i.get("employee"),[])):
						new_employees.append(i)
				if new_employees:
					employees = new_employees.copy()

	employees_list_db = frappe.db.get_list("Employee", filters={"name": ["IN", employee_list]}, fields=["name", "employee_name", "department","date_of_joining"], ignore_permissions=True)
	employees_dict = {}
	for i in employees_list_db:
		employees_dict[i.name] = i

	# make data structure for the roster
	shift_start_time, shift_end_time = frappe.db.get_value("Operations Shift", shift, ["start_time", "end_time"])
	next_day = False
	if shift_start_time > shift_end_time:
		next_day = True
	employees_date_dict = {}
	for i in employees:
		# Ensure employee exists in employees_dict and has date_of_joining
		employee_detail = employees_dict.get(i.get("employee"))
		if employee_detail and employee_detail.get("date_of_joining"):
			if getdate(employee_detail.get("date_of_joining")) <= getdate(i.get("date")):
				if employees_date_dict.get(i["employee"]):
					employees_date_dict[i["employee"]].append({"date":i["date"],
						"start_datetime": datetime.strptime(f"{i['date']} {shift_start_time}", "%Y-%m-%d %H:%M:%S"), "end_datetime":datetime.strptime(f"{add_days(i['date'], 1) if next_day else i['date']} {shift_end_time}", "%Y-%m-%d %H:%M:%S")})
				else:
					employees_date_dict[i["employee"]] =[{"date":i["date"], "start_datetime": datetime.strptime(f"{i['date']} {shift_start_time}", "%Y-%m-%d %H:%M:%S"), "end_datetime":datetime.strptime(f"{add_days(i['date'], 1) if next_day else i['date']} {shift_end_time}", "%Y-%m-%d %H:%M:%S")}]
		else:
			# Log or handle cases where employee details or date_of_joining is missing
			frappe.log_error(f"Employee {i.get('employee')} missing details or date_of_joining.", "Extreme Schedule Data Prep")


	# check for intersection schedules
	error_msg = """"""
	checklist = []
	for emp, dates in employees_date_dict.items():
		datelist = [i["date"] for i in dates]
		if (len(datelist)==1):datelist.append(datelist[0]) # This creates a tuple of (date, date) if only one date, which might not be what SQL IN expects for a single value.
		date_tuple_str = f"('{datelist[0]}')" if len(datelist) == 1 else str(tuple(datelist))
		intersect_query = frappe.db.sql(f"""
			SELECT DISTINCT name, date, start_datetime, end_datetime, shift_type, employee_availability, roster_type
			FROM
			`tabEmployee Schedule` WHERE employee="{emp}" AND date IN {date_tuple_str}
			AND NOT roster_type="{roster_type}"
		""", as_dict=1)
		if intersect_query:
			for iq in intersect_query:
				if not iq.name in checklist:
					if iq.employee_availability=="Working":
						for d_item in dates:
							if d_item["date"] == str(iq.date):
								if (d_item["start_datetime"] <= iq.start_datetime and iq.end_datetime <= d_item["end_datetime"] and iq.end_datetime.date()==d_item["end_datetime"].date()) or \
								   (iq.start_datetime >= d_item["start_datetime"] and  d_item["end_datetime"] <= iq.end_datetime and iq.end_datetime.date()==d_item["end_datetime"].date()) or \
								   (d_item["start_datetime"] >= iq.start_datetime and iq.end_datetime >= d_item["end_datetime"] and iq.end_datetime.date()==d_item["end_datetime"].date()):
									error_msg += f"{emp}, {iq.date}, Requested: <b>{d_item['start_datetime'].strftime('%d-%m-%Y %-I %p')} to {d_item['end_datetime'].strftime('%d-%m-%Y %-I %p')}</b>, Existing: <b>{iq.start_datetime.strftime('%d-%m-%Y %-I %p')} to {iq.end_datetime.strftime('%d-%m-%Y %-I %p')} ({iq.roster_type})</b><hr>\n"
					checklist.append(iq.name)
	if error_msg:
		error_head = f"""
			Some of the schedules you requested with shift <b>{shift}: {shift_start_time} - {shift_end_time}</b> intersect with existing schedule shift time.<br>
			Below list shows: Employee, Date, Requested Schedule and Existing Schedule.
			<hr>
		"""
		frappe.throw(error_head+error_msg)


	if not cint(request_employee_schedule):
		query = """
			INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `employee_name`, `department`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`,
			`operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `start_datetime`, `end_datetime`, `owner`, `modified_by`, `creation`, `modified`)
			VALUES
		"""
		can_create = False
		effective_end_date = getdate(end_date) if end_date else getdate(start_date) 
		list_of_dates_pd = pd.date_range(start=start_date, end=effective_end_date)

		post_data = validate_overfilled_post(list_of_dates_pd, operations_shift_doc.name)
		post_number = post_data.get("post_number")
		schedule_data  = post_data.get("schedule_dict")
		if not post_number:post_number=0
		
		omitted_days = []
				
		# Create a temporary structure to count new schedules per day from the current batch
		daily_add_count = defaultdict(int)
		for emp, date_values in employees_date_dict.items():
			for dateval in date_values:
				daily_add_count[dateval.get("date")] +=1

		query_values = [] # Prepare values for bulk insert
		skipped_ot_no_basic = []
		skipped_ot_overlap = []


		for employee_name_iter, date_values in employees_date_dict.items():
			for datevalue in date_values:
				current_processing_date = datevalue.get("date")

				if roster_type == "Over-Time":
					# Query for existing Basic schedule for this employee and date
					basic_schedule = frappe.db.get_value(
						"Employee Schedule",
						{
							"employee": employee_name_iter,
							"date": current_processing_date,
							"roster_type": "Basic",
							"employee_availability": "Working"
						},
						["start_datetime", "end_datetime"]
					)
					if not basic_schedule:
						skipped_ot_no_basic.append(f"{employee_name_iter} on {current_processing_date}")
						continue 

					# Check for overlap
					ot_start = datevalue.get("start_datetime")
					ot_end = datevalue.get("end_datetime")
					basic_start = basic_schedule[0]
					basic_end = basic_schedule[1]

					# If Over-Time overlaps with Basic, skip scheduling Over-Time
					if not (ot_end <= basic_start or ot_start >= basic_end):
						skipped_ot_overlap.append(f"{employee_name_iter} on {current_processing_date}")
						continue

				if current_processing_date not in omitted_days:
					already_scheduled = int(schedule_data.get(current_processing_date,0))
					num_to_add_this_day = daily_add_count[current_processing_date]

					if num_to_add_this_day + already_scheduled <= post_number:
						employee_doc = employees_dict.get(employee_name_iter)
						name = f"{datevalue['date']}_{employee_name_iter}_{roster_type}"
						query_values.append(f"""
							(
								'{name}', '{employee_name_iter}', '{employee_doc.employee_name}', '{employee_doc.department}', '{datevalue['date']}', '{operations_shift_doc.name}',
								'{operations_shift_doc.site}', '{operations_shift_doc.project}', '{operations_shift_doc.shift_type}', 'Working',
								'{operations_role_doc.name}', '{operations_role_doc.post_abbrv}', '{roster_type}',
								{day_off_ot}, '{datevalue.get('start_datetime')}', '{datevalue.get('end_datetime')}', '{owner}', '{owner}', '{creation}', '{creation}'
							)""")
						can_create = True
					else:
						if current_processing_date not in omitted_days: 
							omitted_days.append(current_processing_date)


		if query_values:
			query += ",\n".join(query_values)
			query += f"""
				ON DUPLICATE KEY UPDATE
				modified_by = VALUES(modified_by),
				modified = VALUES(modified),
				operations_role = VALUES(operations_role),
				post_abbrv = VALUES(post_abbrv),
				roster_type = VALUES(roster_type),
				shift = VALUES(shift),
				project = VALUES(project),
				site = VALUES(site),
				shift_type = VALUES(shift_type),
				day_off_ot = VALUES(day_off_ot),
				employee_availability = "Working",
				start_datetime= VALUES(start_datetime),
				end_datetime= VALUES(end_datetime)
			"""
			if can_create:
				frappe.db.sql(query, values=[])
				frappe.db.commit()
		

		if skipped_ot_no_basic:
			frappe.msgprint("Over-Time schedule was not created for the following because no Basic schedule exists:<br>" + "<br>".join(skipped_ot_no_basic))
		if skipped_ot_overlap:
			frappe.msgprint("Over-Time schedule was not created for the following because it overlaps with Basic schedule:<br>" + "<br>".join(skipped_ot_overlap))


		if omitted_days:
			omitted_days_str = ", ".join(sorted(list(set(omitted_days))))
			frappe.msgprint(f"Employee Schedules were not created for {omitted_days_str} because {operations_shift_doc.name} would have been overfilled if additional schedules were added for these days.")

	else: # request_employee_schedule is true
		from_schedule = frappe.db.get_list(
			"Employee Schedule",
			filters={
				"shift": shift,
				"date": ["BETWEEN", [start_date, end_date if end_date else start_date]],
				"employee": ["IN", employee_list]
			},
			fields=["shift", "site", "project", "employee", "employee_name", "operations_role"],
			group_by="employee DESC" 
		)
		if len(from_schedule):
			if otRoster == "false":
				roster_type_val = "Basic"
			elif otRoster == "true":
				roster_type_val = "Over-Time"

			for emp_item in from_schedule: 
				req_es_doc = frappe.new_doc("Request Employee Schedule")
				req_es_doc.employee = emp_item.employee
				req_es_doc.from_shift = emp_item.shift
				req_es_doc.from_operations_role = emp_item.operations_role
				req_es_doc.to_shift = shift
				req_es_doc.to_operations_role = operations_role_doc.name
				req_es_doc.start_date = start_date
				req_es_doc.end_date = end_date if end_date else start_date
				req_es_doc.roster_type = roster_type_val
				req_es_doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.msgprint("Request Employee Schedule created successfully")

	frappe.enqueue(update_employee_shift, employees=list(employees_date_dict.keys()), shift=shift, owner=owner, creation=creation)


def validate_overfilled_post(date_list_pd, operations_shift_name): 

	dates_unique = list(set(date_list_pd))
	date_list_str = [e.strftime("%Y-%m-%d") for e in dates_unique] 
	
	cond = "" 
	schedule_dict = {}
	base_query = f""" SELECT date ,count(name) as schedule_count from `tabEmployee Schedule`  WHERE shift = "{operations_shift_name}" and employee_availability = "Working" """
	
	post_number_res = frappe.db.sql(f""" SELECT count(name) as post_number from `tabOperations Post` where status = 'Active' and site_shift = '{operations_shift_name}' """,as_dict=1)
	post_number = post_number_res[0].get("post_number") if post_number_res else 0
	
	if not date_list_str: # Handle empty date list
		return{"schedule_dict": schedule_dict, "post_number": post_number}

	if len(date_list_str)==1:
		cond = f" AND date = '{date_list_str[0]}'" 
	elif len(date_list_str)>1:
		# Correctly format tuple for SQL IN clause
		cond = f" AND date in {str(tuple(date_list_str))}"
	
	full_query = base_query + cond + " GROUP BY date" if cond else base_query + " GROUP BY date" 
	
	schedule_number_res = frappe.db.sql(full_query,as_dict=1) 
	for each_item in schedule_number_res: 
		schedule_dict[each_item.get("date").strftime("%Y-%m-%d")] = each_item.schedule_count


	return{"schedule_dict":schedule_dict,"post_number":post_number}

def update_employee_shift(employees, shift, owner, creation):
	"""Update employee assignment"""

	site, project = frappe.get_value("Operations Shift", shift, ["site", "project"])

	if not isinstance(employees, list):
		employees = [emp.get("employee") for emp in employees if emp.get("employee")]


	employees_data = frappe.db.get_list("Employee", filters={"name": ["IN", employees]}, fields=["name", "employee_name", "employee_id", "project", "site", "shift"])
	unmatched_record = {}
	matched_record = []
	no_shift_assigned = []
	for emp in employees_data:
		if emp.project and emp.project != project or emp.site and emp.site != site or emp.shift and emp.shift != shift:
			unmatched_record[emp.name] = emp
		elif emp.project == project and emp.site == site and emp.shift == shift:
			matched_record.append(emp.name)
		else:
			no_shift_assigned.append(emp.name)


	# start with unmatched
	if unmatched_record:
		query = """
			INSERT INTO `tabAdditional Shift Assignment` (`name`, `employee`, `employee_name`, `employee_id`, `site`, `shift`, `project`, `owner`, `modified_by`, `creation`, `modified`)
			VALUES
		"""
		query_values_asa = []
		for k, emp_asa in unmatched_record.items():
			query_values_asa.append(f"""(
					"{emp_asa.name}|{shift}", "{emp_asa.name}", "{emp_asa.employee_name}", "{emp_asa.employee_id}", "{site}", "{shift}",
					"{project}", "{owner}", "{owner}", "{creation}", "{creation}"
			)""")
		
		if query_values_asa:
			query += ",\n".join(query_values_asa)
			query += """
				ON DUPLICATE KEY UPDATE
				project = VALUES(project),
				site = VALUES(site),
				shift = VALUES(shift),
				modified_by = VALUES(modified_by),
				modified = VALUES(modified)
			"""
			frappe.db.sql(query)

	if matched_record:
		frappe.db.delete("Additional Shift Assignment", {
			"employee": ["IN", matched_record]
		})

	if no_shift_assigned:
		for employee_name_iter2 in no_shift_assigned:
			""" This function updates the employee project, site and shift in the employee doctype """
			frappe.db.set_value("Employee", employee_name_iter2, {"project":project, "site":site, "shift":shift})

	frappe.db.commit()


@frappe.whitelist()
def schedule_leave(employees, leave_type, start_date, end_date):
	try:
		for employee_item in json.loads(employees):
			for date_item in pd.date_range(start=start_date, end=end_date):
				date_str = cstr(date_item.date())
				if frappe.db.exists("Employee Schedule", {"employee": employee_item["employee"], "date": date_str}):
					roster = frappe.get_doc("Employee Schedule", {"employee": employee_item["employee"], "date": date_str})
					roster.shift = None
					roster.shift_type = None
					roster.project = None
					roster.site = None
				else:
					roster = frappe.new_doc("Employee Schedule")
					roster.employee = employee_item["employee"]
					roster.date = date_str
				roster.employee_availability = leave_type
				roster.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Schedule Leave Error")
		response("error", 500, None, str(e))


@frappe.whitelist(allow_guest=True)
def unschedule_staff(employees, roster_type, start_date=None, end_date=None, never_end=0, selected_days_only=0):
	try:
		_start_date = getdate(start_date) if start_date else None
		stop_date = getdate(end_date) if end_date else None

		employees = json.loads(employees)

		if not employees:
			response("Error", 400, None, {"message": "Employees must be selected."})

		if not selected_days_only and not _start_date:
			frappe.throw("Must provide a start date if selected days are not targetted")

		if _start_date:
			employees = [i for i in employees if getdate(i["date"])>=_start_date]

		if end_date:
			employees = [i for i in employees if getdate(i["date"])<=stop_date]

		# If roster type is "Basic" then delete Basic/Over-Time schedules otherwise delete only target roster type schedules
		roster_type_query = "roster_type in ('Basic', 'Over-Time')" if roster_type == "Basic" else f"roster_type = '{roster_type}'"

		# check if no end date
		if cint(never_end) == 1:
			employees_to_delete = []
			for i in employees:
				if not i["employee"] in employees_to_delete:
					employees_to_delete.append(i["employee"])
			# delete all schedules greater than start date
			employees_to_delete=str(tuple(employees_to_delete)).replace(",)", ")")
			frappe.db.sql(f"""
				DELETE FROM `tabEmployee Schedule` WHERE employee IN {employees_to_delete} and date>="{start_date}" and {roster_type_query}
			""")
		else:
			for i in employees:
				frappe.db.sql(f"""
					DELETE FROM `tabEmployee Schedule` WHERE employee="{i["employee"]}" and date="{i["date"]}" and {roster_type_query}
				""")
		response("Success", 200, {"message":"Staff(s) unscheduled successfully"})
	except Exception as e:
		frappe.throw(str(e))
		response("Error", 200, None, str(e))


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

		plan_post(posts, args)
		return response("Success", 200, {"message": "Post Planned Successfully"})

	elif args.post_status == "Cancel Post":
		if args.cancel_end_date and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))

		if not args.cancel_end_date and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		frappe.enqueue(cancel_post,posts=posts, args=args, is_async=True, queue="long", at_front=True, timeout=3600)

	elif args.post_status == "Suspend Post":
		if args.suspend_to_date and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))

		if not args.suspend_to_date and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		frappe.enqueue(suspend_post, posts=posts, args=args, is_async=True, queue="long", at_front=True, timeout=3600)

	elif args.post_status == "Post Off":
		if args.repeat_till and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))

		if args.repeat not in ["Does not repeat", "Selected Days Only"] and not args.repeat_till and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))

		if args.repeat == "Does not repeat" and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and choose 'Does not repeat' option!"))

		post_off(posts=posts, args=args)
		return response("Success", 200, {"message": "Post Off Marked Successfully"})

	frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long", timeout=3600)
	return response("Success", 200, {"message": "Your request is being processed in the background."})

def plan_post(posts, args):
	""" This function sets the post status to planned provided a post, start date and an end date """

	end_date_val = args.plan_end_date if args.plan_end_date and not cint(args.project_end_date) else None
	posts_list = json.loads(posts)

	# Extract unique posts
	unique_posts_list = list(set(post["post"] for post in posts_list))

	# Fetch all projects linked to posts
	post_projects = {
		p["name"]: p["project"] for p in frappe.get_all(
			"Operations Post",
			filters={"name": ["in", unique_posts_list]},
			fields=["name", "project"]
		)
	}

	# If project_end_date is set, get contract end dates in bulk
	if cint(args.project_end_date) and not args.plan_end_date:
		project_names = list(post_projects.values())
		if project_names: 
			contract_end_dates = frappe.get_all(
				"Contracts",
				filters={"project": ["in", project_names]},
				fields=["project", "end_date"],
				as_list=True 
			)
			contract_map = dict(contract_end_dates) # Convert list of lists/tuples to dict

			for post_name_iter in unique_posts_list: 
				project_val = post_projects.get(post_name_iter) 
				if project_val:
					end_date_val = contract_map.get(project_val)
					if not end_date_val:
						frappe.throw(_("No end date set for contract linked to project {0}".format(project_val)))
		else: # No projects, so can"t determine end_date from project
			if not args.plan_end_date: # If no specific end date is provided either
				 frappe.throw(_("No projects found to determine project end date, and no specific end date provided."))


	if not end_date_val:
		frappe.throw(_("No end date specified."))

	# Collect all dates and posts for bulk processing
	existing_schedules = frappe.get_all(
		"Post Schedule",
		filters={
			"date": ["between", [args.plan_from_date, end_date_val]],
			"post": ["in", unique_posts_list]
		},
		fields=["name", "post", "date"]
	)

	# Create a set for quick lookup
	existing_schedules_set = {(s["post"], cstr(s["date"])): s["name"] for s in existing_schedules}

	creation = now()
	owner = frappe.session.user
	operations_role_val = ""
	shift_val = "" 
	post_abbrv_val = "" 
	site_val = "" 
	project_detail_val = "" 
	previous_post = ""
	insert_post_flag = False 
	delete_post_list = []

	insert_query = """
		Insert Into
			`tabPost Schedule`
			(
				`name`, `post`, `operations_role`, `post_abbrv`, `shift`, `site`,
				`project`, `date`, `post_status`, `owner`, `modified_by`, `creation`, `modified`
			)
		Values
	"""
	query_values_plan = []

	for post_name_iter2 in unique_posts_list: 
		if previous_post != post_name_iter2:
			previous_post = post_name_iter2
			post_details_val = get_post_details(post_name_iter2) 
			if post_details_val:
				operations_role_val = post_details_val["post_template"]
				shift_val = post_details_val["site_shift"]
				post_abbrv_val = post_details_val["post_abbrv"]
				site_val = post_details_val["site"]
				project_detail_val = post_details_val["project"]

		for date_item in pd.date_range(start=args.plan_from_date, end=end_date_val): 
			date_str = cstr(date_item.date())
			if (post_name_iter2, date_str) in existing_schedules_set:
				delete_post_list.append(existing_schedules_set[(post_name_iter2, date_str)])

			name = f"{post_name_iter2}_{date_str}"
			query_values_plan.append(f"""
				(
					"{name}", "{post_name_iter2}", "{operations_role_val}", "{post_abbrv_val}", "{shift_val}", "{site_val}",
					"{project_detail_val}", "{date_str}", "Planned", "{owner}", "{owner}", "{creation}", "{creation}"
				)""")
			insert_post_flag = True
	
	if insert_post_flag and query_values_plan:
		insert_query += ",\n".join(query_values_plan)

		insert_query += f"""
			On Duplicate Key Update
			modified_by = Values(modified_by),
			modified = "{creation}",
			operations_role = Values(operations_role),
			post_abbrv = Values(post_abbrv),
			shift = Values(shift),
			project = Values(project),
			site = Values(site),
			post_status = "Planned",
			date= Values(date)
		"""

		if delete_post_list: # Check if list is not empty
			frappe.db.delete("Post Schedule", {"name": ["in", list(set(delete_post_list))]})
		frappe.db.sql(insert_query) 
		frappe.db.commit()

def cancel_post(posts, args):
	end_date_val = None 

	if args.cancel_end_date and not cint(args.project_end_date):
		end_date_val = args.cancel_end_date

	for post_item in json.loads(posts): 
		if cint(args.project_end_date) and not args.cancel_end_date:
			project_val = frappe.db.get_value("Operations Post", post_item["post"], ["project"]) 
			if frappe.db.exists("Contracts", {"project": project_val}):
				contract, contract_end_date = frappe.db.get_value("Contracts", {"project": project_val}, ["name", "end_date"]) 
				if not contract_end_date:
					frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
				end_date_val = contract_end_date # Assign to outer scope
			else:
				frappe.throw(_("No contract linked with project {project}".format(project=project_val)))

		if not end_date_val: # Ensure end_date is set before proceeding
			frappe.throw(_("End date for cancellation not determined."))
			
		for date_item in pd.date_range(start=args.cancel_from_date, end=end_date_val):
			date_str = cstr(date_item.date()) 
			if frappe.db.exists("Post Schedule", {"date": date_str, "post": post_item["post"]}):
				delete_existing_post_schedules(date_str, post_item["post"])

			doc = frappe.new_doc("Post Schedule")
			doc.post = post_item["post"]
			doc.date = date_str
			doc.paid = args.suspend_paid 
			doc.post_status = "Cancelled"
			doc.save(ignore_permissions=True)
	frappe.db.commit()

def suspend_post(posts, args):
	end_date_val = None 

	if args.suspend_to_date and not cint(args.project_end_date):
		end_date_val = args.suspend_to_date

	for post_item in json.loads(posts):
		if cint(args.project_end_date) and not args.suspend_to_date:
			project_val = frappe.db.get_value("Operations Post", post_item["post"], ["project"]) 
			if frappe.db.exists("Contracts", {"project": project_val}):
				contract, contract_end_date = frappe.db.get_value("Contracts", {"project": project_val}, ["name", "end_date"]) 
				if not contract_end_date:
					frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
				end_date_val = contract_end_date 
			else:
				frappe.throw(_("No contract linked with project {project}".format(project=project_val)))
		
		if not end_date_val: # Ensure end_date is set
			 frappe.throw(_("End date for suspension not determined."))

		for date_item in pd.date_range(start=args.suspend_from_date, end=end_date_val): 
			date_str = cstr(date_item.date()) 
			if frappe.db.exists("Post Schedule", {"date": date_str, "post": post_item["post"]}):
				delete_existing_post_schedules(date_str, post_item["post"])

			doc = frappe.new_doc("Post Schedule")
			doc.post = post_item["post"]
			doc.date = date_str
			doc.paid = args.suspend_paid

			doc.post_status = "Suspended"
			doc.save(ignore_permissions=True)
	frappe.db.commit()

def post_off(posts, args):
	if args.repeat:
		posts_list = json.loads(posts)
		# Extract unique posts
		unique_posts_list = list(set(post["post"] for post in posts_list))

		# Fetch all projects linked to posts
		post_projects = get_post_porjects(unique_posts_list)

		end_date_val = get_post_schedule_end_date(args, unique_posts_list, post_projects) 
		if not end_date_val:
			frappe.throw(_("No end date specified."))

		# Collect all dates and posts for bulk processing
		existing_schedules = get_existing_post_schedules(args, end_date_val, unique_posts_list)

		# Create a set for quick lookup
		existing_schedules_set = {(s["post"], cstr(s["date"])): s["name"] for s in existing_schedules}

		insert_post_schedule(args, unique_posts_list, existing_schedules_set, end_date_val, posts_list)

def get_post_porjects(unique_posts_list):
	if not unique_posts_list: return {} 
	return {
		p["name"]: p["project"] for p in frappe.get_all(
			"Operations Post",
			filters={"name": ["in", unique_posts_list]},
			fields=["name", "project"]
		)
	}

def get_post_schedule_end_date(args, unique_posts_list, post_projects={}):
	end_date_val = args.repeat_till if args.repeat_till and not cint(args.project_end_date) else None 

	# This was plan_from_date, assuming it should be post_off_from_date from context of post_off args
	from_date_for_logic = args.post_off_from_date if "post_off_from_date" in args else args.plan_from_date

	if args.repeat in ["Does not repeat", "Selected Days Only"]:
		end_date_val = get_last_day(from_date_for_logic)


	# If project_end_date is set, get contract end dates in bulk
	if cint(args.project_end_date) and post_projects and not (args.repeat_till if "repeat_till" in args else None): # Check specific end date for this flow
		project_names = list(post_projects.values())
		if project_names: # Ensure there are projects
			contract_end_dates = frappe.get_all(
				"Contracts",
				filters={"project": ["in", project_names]},
				fields=["project", "end_date"],
				as_list=True
			)
			contract_map = dict(contract_end_dates)
			applicable_end_dates = [contract_map.get(proj) for proj in project_names if contract_map.get(proj)]
			if applicable_end_dates:
				end_date_val = min(applicable_end_dates) 
			else: # No contract end dates found for the projects
				if not args.repeat_till : # If no specific override date is given
					frappe.throw(_("No contract end dates found for associated projects, and no specific 'Repeat Till' date provided."))
		elif not args.repeat_till: # No projects and no specific end date
			 frappe.throw(_("No projects to determine project end date, and no specific 'Repeat Till' date provided."))


	return end_date_val

def get_existing_post_schedules(args, end_date, unique_posts_list):
	if not unique_posts_list: return [] 
	# Assuming plan_from_date should be post_off_from_date for post_off context
	from_date_for_query = args.post_off_from_date if "post_off_from_date" in args else args.plan_from_date
	return frappe.get_all(
		"Post Schedule",
		filters={
			"date": ["between", [from_date_for_query, end_date]],
			"post": ["in", unique_posts_list]
		},
		fields=["name", "post", "date"]
	)

def insert_post_schedule(args, unique_posts_list, existing_schedules_set, end_date, posts_orig_list): 
	from one_fm.api.mobile.roster import month_range
	creation = now()
	owner = frappe.session.user
	post_details_val = {"post_template": "", "site_shift": "", "site": "", "project": "", "post_abbrv": ""} 
	previous_post = ""
	insert_post_flag = False
	delete_post_list = [] 
	week_days = get_week_days(args)
	post_date_map = {}
	if args.repeat in ["Monthly", "Yearly", "Does not repeat", "Selected Days Only"]:
		post_date_map = get_post_date_map(unique_posts_list, posts_orig_list)

	insert_query = get_insert_post_schedule_query_prefix()
	query_values_insert = [] 
	for post_name_iter3 in unique_posts_list: 
		if previous_post != post_name_iter3:
			previous_post = post_name_iter3
			post_details_val=get_post_details(post_name_iter3)

		# Ensure post_details_val is not None before proceeding
		if not post_details_val: post_details_val = {"post_template": "", "site_shift": "", "site": "", "project": "", "post_abbrv": ""}


		if args.repeat in ["Monthly", "Yearly", "Does not repeat", "Selected Days Only"]:
			for post_date_iter in post_date_map.get(post_name_iter3, []): 
				if args.repeat == "Monthly":
					for date_item in month_range(post_date_iter, end_date):
						date_str = cstr(date_item.date())
						delete_post_list = get_delete_posts(post_name_iter3, date_str, existing_schedules_set, delete_post_list)
						query_values_insert.append(get_insert_post_schedule_query(post_name_iter3, date_str, post_details_val, args, owner, creation))
						insert_post_flag = True
				elif args.repeat == "Yearly":
					for date_item in pd.date_range(start=post_date_iter, end=end_date, freq=pd.DateOffset(years=1)): 
						date_str = cstr(date_item.date())
						delete_post_list = get_delete_posts(post_name_iter3, date_str, existing_schedules_set, delete_post_list)
						query_values_insert.append(get_insert_post_schedule_query(post_name_iter3, date_str, post_details_val, args, owner, creation))
						insert_post_flag = True
				elif args.repeat in ["Does not repeat", "Selected Days Only"]:
					delete_post_list = get_delete_posts(post_name_iter3, post_date_iter, existing_schedules_set, delete_post_list)
					query_values_insert.append(get_insert_post_schedule_query(post_name_iter3, post_date_iter, post_details_val, args, owner, creation))
					insert_post_flag = True

		if args.repeat in ["Daily", "Weekly"]:
			# Use post_off_from_date from args for this specific logic path
			start_date_for_loop = args.post_off_from_date if "post_off_from_date" in args else args.plan_from_date # Fallback if not present
			for date_item in pd.date_range(start=start_date_for_loop, end=end_date):
				if args.repeat == "Weekly" and getdate(date_item).strftime("%A") not in week_days: 
					continue
				date_str = cstr(date_item.date())
				delete_post_list = get_delete_posts(post_name_iter3, date_str, existing_schedules_set, delete_post_list)
				query_values_insert.append(get_insert_post_schedule_query(post_name_iter3, date_str, post_details_val, args, owner, creation))
				insert_post_flag = True
	
	if insert_post_flag and query_values_insert:
		insert_query += ",\n".join(query_values_insert)
		insert_query = get_insert_post_schedule_query_tail_end(insert_query, creation)
		if delete_post_list:
			frappe.db.delete("Post Schedule", {"name": ["in", list(set(delete_post_list))]}) 
		frappe.db.sql(insert_query) 
		frappe.db.commit()

def get_week_days(args):
	week_days = []
	if args.repeat == "Weekly":
		if args.sunday: week_days.append("Sunday")
		if args.monday: week_days.append("Monday")
		if args.tuesday: week_days.append("Tuesday")
		if args.wednesday: week_days.append("Wednesday")
		if args.thursday: week_days.append("Thursday")
		if args.friday: week_days.append("Friday")
		if args.saturday: week_days.append("Saturday")
	return week_days

def get_post_date_map(unique_posts_list, posts_orig_list): 
	post_date_map = {}
	for post_name_iter4 in unique_posts_list: 
		post_date_map[post_name_iter4] = [p["date"] for p in posts_orig_list if p["post"] == post_name_iter4]
	return post_date_map

def get_insert_post_schedule_query_prefix():
	return """
		Insert Into
			`tabPost Schedule`
			(
				`name`, `post`, `operations_role`, `post_abbrv`, `shift`, `site`,
				`project`, `paid`, `date`, `post_status`, `owner`, `modified_by`, `creation`, `modified`
			)
		Values
	"""

def get_post_details(post_name_arg):
	post_details_val = frappe.db.get_value(
		"Operations Post",
		post_name_arg,
		["post_template", "site_shift", "site", "project"],
		as_dict=True
	)
	if post_details_val:
		if post_details_val.get("post_template"):
			post_details_val["post_abbrv"] = frappe.db.get_value("Operations Role", post_details_val["post_template"], ["post_abbrv"])
		else:
			post_details_val["post_abbrv"] = "" 
		return post_details_val
	return {"post_template": "", "site_shift": "", "site": "", "project": "", "post_abbrv": ""}


def get_delete_posts(post_name_arg, date_str, existing_schedules_set, delete_post_list_arg=None): 
	if delete_post_list_arg is None:
		delete_post_list_arg = []
	if (post_name_arg, date_str) in existing_schedules_set:
		delete_post_list_arg.append(existing_schedules_set[(post_name_arg, date_str)])
	return delete_post_list_arg


def get_insert_post_schedule_query(post_name_arg, date_str, post_details_arg, args, owner, creation):
	name = f"{post_name_arg}_{date_str}"
	pt = post_details_arg.get("post_template", "") if post_details_arg else ""
	pa = post_details_arg.get("post_abbrv", "") if post_details_arg else ""
	ss = post_details_arg.get("site_shift", "") if post_details_arg else ""
	s = post_details_arg.get("site", "") if post_details_arg else ""
	p = post_details_arg.get("project", "") if post_details_arg else ""
	
	return f"""(
			"{name}", "{post_name_arg}", "{pt}", "{pa}",
			"{ss}", "{s}", "{p}",
			"{args.post_off_paid}", "{date_str}", "Post Off", "{owner}", "{owner}", "{creation}", "{creation}"
		)"""


def get_insert_post_schedule_query_tail_end(insert_query_arg, creation):
	insert_query_arg += f"""
		On Duplicate Key Update
		modified_by = Values(modified_by),
		modified = "{creation}",
		operations_role = Values(operations_role),
		post_abbrv = Values(post_abbrv),
		shift = Values(shift),
		project = Values(project),
		site = Values(site),
		post_status = "Post Off",
		date= Values(date)
	"""
	return insert_query_arg

def delete_existing_post_schedules(date_str_arg,post_name_arg):
	try:
		frappe.db.sql(f"""DELETE from `tabPost Schedule` where date = "{date_str_arg}" and post = "{post_name_arg}" """)
		frappe.db.commit()
	except:
		frappe.log_error("Error Deleting Post Schedules",frappe.get_traceback())

@frappe.whitelist()
def dayoff(employees, client_day_off=0, selected_dates=0, selected_reliever=None, repeat=0, repeat_freq=None, week_days=[], repeat_till=None, project_end_date=None):
	try:
		creation = now()
		owner = frappe.session.user
		roster_type = "Basic"
		employee_availability = "Client Day Off" if cint(client_day_off) else "Day Off"

		query_values_dayoff = []
		roster_list=[]

		if not repeat_till and not cint(project_end_date) and not cint(selected_dates):
			frappe.throw(_("Please select either a repeat till date, check the project end date option, or select specific dates."))

		from one_fm.api.mobile.roster import month_range
		if cint(selected_dates):
			for employee_item in json.loads(employees): 
				date_val = employee_item["date"]
				start_date_val = getdate(date_val) 
				month_end_date = get_last_day(start_date_val)
				emp_query = f"""
					   SELECT *
					   FROM `tabEmployee Schedule`
					   WHERE `employee` = "{employee_item["employee"]}" AND `date` = "{date_val}"
				   """
				try:
					roster_data = frappe.db.sql(emp_query, as_dict=True)[0]
				except IndexError: # Handle case where query returns no results
					roster_data = get_shift_details_of_employee(employee_item["employee"],date_val)
				roster_list.append(roster_data)

				if getdate(date_val) > getdate(today()):
					name = f"{date_val}_{employee_item['employee']}_{roster_type}"
					query_values_dayoff.append(f"""(
						"{name}", "{employee_item["employee"]}", "{date_val}", "", "", "",
						"", "{employee_availability}", "", "", "Basic",
						0, "{owner}", "{owner}", "{creation}", "{creation}"
					)""")
					update_day_off_ot_doc = frappe.db.get_value("Employee Schedule",
					{
						"employee": employee_item["employee"],
						"day_off_ot": 1,
						"date": ["between", [start_date_val, month_end_date]],
					}, "name") # Get name for set_value
					if update_day_off_ot_doc:
						frappe.db.set_value("Employee Schedule", update_day_off_ot_doc, "day_off_ot", 0)
		else: # Not selected_dates
			effective_end_date = None 
			if repeat_till and not cint(project_end_date):
				effective_end_date = getdate(repeat_till)

			for employee_item in json.loads(employees):
				current_employee_date = getdate(employee_item["date"]) 

				if cint(project_end_date) and not (repeat_till and not cint(project_end_date)): # Only if project_end_date is sole determinant
					project_val = frappe.db.get_value("Employee", employee_item["employee"], "project")
					if project_val and frappe.db.exists("Contracts", {"project": project_val}):
						contract, contract_end_date = frappe.db.get_value("Contracts", {"project": project_val}, ["name", "end_date"]) 
						if not contract_end_date:
							frappe.throw(_("No end date set for contract {contract}".format(contract=contract)))
						effective_end_date = getdate(contract_end_date)
					elif not project_val : # No project for employee
						 frappe.throw(_("Employee {0} has no project assigned to determine project end date.".format(employee_item["employee"])))
					else: # No contract for project
						frappe.throw(_("No contract linked with project {project} to determine project end date.".format(project=project_val)))
				
				if not effective_end_date: # If still no end date after potentially checking project end date
					frappe.throw(_("An end date for the Day Off repetition must be established."))


				if repeat and repeat_freq == "Weekly":
					for date_iter in pd.date_range(start=current_employee_date, end=effective_end_date):
						month_end_date_iter = get_last_day(getdate(date_iter)) 
						if getdate(date_iter).strftime("%A") in week_days and getdate(date_iter) > getdate(today()):
							name = f"{date_iter.date()}_{employee_item['employee']}_{roster_type}"
							query_values_dayoff.append(f"""(
								"{name}", "{employee_item["employee"]}", "{date_iter.date()}", "", "", "",
								"", "{employee_availability}", "", "", "Basic",
								0, "{owner}", "{owner}", "{creation}", "{creation}"
							)""")
							# Roster data for reliever assignment (if any)
							emp_query_weekly = f"SELECT * FROM `tabEmployee Schedule` WHERE `name` = '{name}'"
							try: roster_data_weekly = frappe.db.sql(emp_query_weekly, as_dict=True)[0]
							except IndexError: roster_data_weekly = get_shift_details_of_employee(employee_item["employee"],date_iter.date())
							if roster_data_weekly not in roster_list: roster_list.append(roster_data_weekly)
							
							update_day_off_ot_doc_weekly = frappe.db.get_value("Employee Schedule", 
							{
								"employee": employee_item["employee"],
								"day_off_ot": 1,
								"date": ["between", [date_iter.date(), month_end_date_iter]],
							}, "name")
							if update_day_off_ot_doc_weekly:
								frappe.db.set_value("Employee Schedule", update_day_off_ot_doc_weekly, "day_off_ot", 0)

				elif repeat and repeat_freq == "Monthly":
					for date_iter in month_range(current_employee_date, effective_end_date):
						month_end_date_iter = get_last_day(getdate(date_iter))
						if getdate(date_iter) > getdate(today()):
							name = f"{date_iter.date()}_{employee_item['employee']}_{roster_type}"
							query_values_dayoff.append(f"""(
								"{name}", "{employee_item["employee"]}", "{date_iter.date()}", "", "", "",
								"", "{employee_availability}", "", "", "Basic",
								0, "{owner}", "{owner}", "{creation}", "{creation}"
							)""")
							# Roster data for reliever assignment
							emp_query_monthly = f"SELECT * FROM `tabEmployee Schedule` WHERE `name` = '{name}'"
							try: roster_data_monthly = frappe.db.sql(emp_query_monthly, as_dict=True)[0]
							except IndexError: roster_data_monthly = get_shift_details_of_employee(employee_item["employee"],date_iter.date())
							if roster_data_monthly not in roster_list: roster_list.append(roster_data_monthly)

							update_day_off_ot_doc_monthly = frappe.db.get_value("Employee Schedule", 
							{
								"employee": employee_item["employee"],
								"day_off_ot": 1,
								"date": ["between", [date_iter.date(), month_end_date_iter]],
							}, "name")
							if update_day_off_ot_doc_monthly:
								frappe.db.set_value("Employee Schedule", update_day_off_ot_doc_monthly, "day_off_ot", 0)
		
		if query_values_dayoff:
			query_main = """
				INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`,
				`operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `owner`, `modified_by`, `creation`, `modified`)
				VALUES 
			""" 
			query_main += ",\n".join(query_values_dayoff)
			query_main += f"""
				ON DUPLICATE KEY UPDATE
				modified_by = VALUES(modified_by),
				modified = "{creation}",
				operations_role = "",
				post_abbrv = "",
				roster_type = "Basic", 
				shift = "",
				project = "",
				site = "",
				shift_type = "",
				day_off_ot = 0,
				employee_availability = "{employee_availability}"
			"""
			frappe.db.sql(query_main) 
			frappe.db.commit()

		if selected_reliever:			
			if frappe.db.exists("Employee", selected_reliever):
				reliever_roster_assignment(selected_reliever, roster_list)
			else:
				frappe.msgprint(f"Reliever with Employee ID {selected_reliever} not found.")

		return response("success", 200, {"message":"Days Off set successfully."}) 
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Day Off Error")
		return response("error", 500, None, str(e)) 
	

def reliever_roster_assignment(reliver_emp_name, roster_list_arg): 
	day_off_ot = 0
	request_employee_schedule = 0
	keep_days_off = 0
	employee_list_for_extreme = [reliver_emp_name]
	otRoster = "false"
	for roster_data_item in roster_list_arg:
		if roster_data_item and roster_data_item.get("shift") and roster_data_item.get("operations_role") and \
		   roster_data_item.get("start_datetime") and roster_data_item.get("end_datetime") and roster_data_item.get("date"):
			
			shift_val = roster_data_item["shift"]
			operations_role_val = roster_data_item["operations_role"]
			start_date_val = roster_data_item["start_datetime"].date() if isinstance(roster_data_item["start_datetime"], datetime) else getdate(roster_data_item["start_datetime"]).date()
			end_date_val = roster_data_item["end_datetime"].date() if isinstance(roster_data_item["end_datetime"], datetime) else getdate(roster_data_item["end_datetime"]).date()
			
			# Ensure date is correctly formatted string YYYY-MM-DD
			date_val_str = roster_data_item["date"].strftime("%Y-%m-%d") if isinstance(roster_data_item["date"], (datetime, pd.Timestamp)) else cstr(roster_data_item["date"])
			
			employees_for_extreme = [{"employee":reliver_emp_name,"date":date_val_str}]

			extreme_schedule(employees_for_extreme, shift_val, operations_role_val, otRoster, 
				start_date_val.strftime("%Y-%m-%d"),
				end_date_val.strftime("%Y-%m-%d"), 
				keep_days_off, day_off_ot,
				request_employee_schedule, employee_list_for_extreme, selected_reliever=reliver_emp_name)
		else:
			frappe.log_error(f"Skipping reliever assignment due to incomplete roster_data: {roster_data_item}", "Reliever Assignment")


def get_shift_details_of_employee(emp_name_arg, date_arg):
	emp_project, emp_site, emp_shift, designation = frappe.db.get_value("Employee", emp_name_arg, ["project", "site", "shift", "designation"])
	if not emp_shift:
		frappe.log_error(f"Employee {emp_name_arg} has no default shift assigned.", "Get Shift Details")
		return None # Or raise error, or return a default structure

	operations_shift_doc = frappe.get_doc("Operations Shift",emp_shift, ignore_permissions=True)
	
	# Ensure date_arg is a string in "YYYY-MM-DD" format for strptime
	date_str = cstr(date_arg)
	if isinstance(date_arg, datetime): date_str = date_arg.strftime("%Y-%m-%d")
	elif isinstance(date_arg, pd.Timestamp): date_str = date_arg.strftime("%Y-%m-%d")


	start_datetime = datetime.strptime(f"{date_str} {operations_shift_doc.start_time}", "%Y-%m-%d %H:%M:%S")
	end_datetime = datetime.strptime(f"{date_str} {operations_shift_doc.end_time}", "%Y-%m-%d %H:%M:%S")

	operation_role_name = frappe.get_value( 
		"Operations Role",
		filters={
			"shift": emp_shift,
			"project": emp_project,
			"post_name": designation 
		},
		fieldname="name"
	)
	# If no specific role found, maybe a default or log
	if not operation_role_name:
		# Fallback: try finding a role only by shift if the specific one isn"t found
		operation_role_name = frappe.get_value("Operations Role", {"shift": emp_shift, "status":"Active"}, "name")
		if not operation_role_name:
			frappe.log_error(f"No matching Operations Role for emp {emp_name_arg}, shift {emp_shift}, designation {designation}, project {emp_project}", "Get Shift Details")
			return {
				"date": getdate(date_str), 
				"shift": emp_shift,
				"operations_role": None,
				"start_datetime":start_datetime,
				"end_datetime":end_datetime
			}


	dict_value = {"date":getdate(date_str),"shift":emp_shift,"operations_role":operation_role_name,"start_datetime":start_datetime,"end_datetime":end_datetime}
	return dict_value


@frappe.whitelist()
def assign_staff(employees, shift, custom_is_reliever, custom_operations_role_allocation=None, request_employee_assignment=None):
	if not employees:
		frappe.throw("Please select employees first")
	
	shift_name_val, site_val, project_val = frappe.db.get_value("Operations Shift", shift, ["name", "site", "project"]) 
	
	try:
		employees_list_json = json.loads(employees)
		for employee_name_iter in employees_list_json:
			if not cint(request_employee_assignment):
				frappe.enqueue(assign_job, employee=employee_name_iter, shift=shift_name_val, site=site_val, project=project_val, 
							   custom_operations_role_allocation=custom_operations_role_allocation, 
							   custom_is_reliever=custom_is_reliever, is_async=True, queue="long")
			else:
				emp_project_db, emp_site_db, emp_shift_db = frappe.db.get_value("Employee", employee_name_iter, ["project", "site", "shift"])

				if emp_project_db != project_val or emp_site_db != site_val or emp_shift_db != shift_name_val:
					frappe.enqueue(create_request_employee_assignment, employee=employee_name_iter, 
								   from_shift=emp_shift_db, to_shift=shift_name_val, is_async=True, queue="long")
		
		frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long")
		return response("Success", 200, {"message": "Assignment request processed."})

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Assign Staff Error")
		return response("Error", 500, None, str(e))


def create_request_employee_assignment(employee, from_shift, to_shift):
	req_ea_doc = frappe.new_doc("Request Employee Assignment")
	req_ea_doc.employee = employee
	req_ea_doc.from_shift = from_shift
	req_ea_doc.to_shift = to_shift
	req_ea_doc.save(ignore_permissions=True)
	frappe.db.commit() 


def assign_job(employee, shift, site, project, custom_operations_role_allocation, custom_is_reliever):
	update_values = {
		"shift": shift,
		"site": site,
		"project": project,
		"custom_operations_role_allocation": custom_operations_role_allocation,
		"custom_is_reliever": custom_is_reliever
	}
	frappe.db.set_value("Employee", employee, update_values)
	frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def search_staff(key, search_term):
	conds = ""
	# Use query parameters to prevent SQL injection vulnerabilities
	sql_params = {}

	if key == "customer" and search_term:
		conds += "AND prj.customer LIKE %(customer)s AND emp.project=prj.name"
		sql_params["customer"] = f"%{search_term}%"
	elif key == "employee_id" and search_term:
		conds += "AND emp.employee_id LIKE %(employee_id)s "
		sql_params["employee_id"] = f"%{search_term}%"
	elif key == "project" and search_term:
		conds += "AND emp.project LIKE %(project)s "
		sql_params["project"] = f"%{search_term}%"
	elif key == "site" and search_term:
		conds += "AND emp.site LIKE %(site)s "
		sql_params["site"] = f"%{search_term}%"
	elif key == "employee_name" and search_term:
		conds += "AND emp.employee_name LIKE %(name)s "
		sql_params["name"] = f"%{search_term}%"
	else: 
		return []


	data = frappe.db.sql(f"""
		SELECT
			DISTINCT emp.name, emp.employee_id, emp.employee_name, emp.image, 
			emp.one_fm_nationality as nationality, usr.mobile_no, usr.name as email, 
			emp.designation, emp.department, emp.shift, emp.site, emp.project
		FROM `tabEmployee` AS emp
		JOIN `tabUser` AS usr ON emp.user_id = usr.name
		LEFT JOIN `tabProject` AS prj ON emp.project = prj.name
		WHERE 1=1 
		{conds}
	""", values=sql_params, as_dict=1)
	return data

@frappe.whitelist()
def get_employee_detail(employee_pk):
	if employee_pk:
		employee_data = frappe.db.get_value("Employee", employee_pk, 
											["name", "employee_id", "employee_name", "enrolled", "cell_number"], 
											as_dict=1)
		if employee_data:
			return employee_data 
	return None 


def create_employee_schedule():
	"""
	Generate employee schedules for the month after the next.
	"""
	# Determine the target month (month after next)
	today_date = getdate(nowdate()) 
	target_month_start = get_first_day(add_months(today_date, 1))
	target_month_end = get_last_day(add_months(today_date, 1))

	shifts_with_auto_roster = frappe.get_all(
	"Operations Shift",
	filters={"automate_roster": 1},
	fields=["name"]
	)

	shift_names = [shift["name"] for shift in shifts_with_auto_roster]

	if shift_names:
		employees_auto_roster = frappe.get_all(
		"Employee",
		filters={"shift": ["in", shift_names], "status": "Active"}, # Added Active status filter
		fields=["name", "employee_name", "department", "day_off_category", "number_of_days_off", "custom_operations_role_allocation", "shift"]
		)

		for employee_doc in employees_auto_roster:
			total_days = date_diff(target_month_end, target_month_start) + 1 # Use target_month_end

			if not employee_doc.shift or not employee_doc.custom_operations_role_allocation:
				frappe.log_error(
					f"Missing shift or operations role for employee {employee_doc.name}",
					"Employee Schedule Creation Error"
				)
				continue

			try: # Add try-except for Doctype fetching
				operations_shift_doc = frappe.get_doc("Operations Shift", employee_doc.shift, ignore_permissions=True)
				operations_role_doc = frappe.get_doc("Operations Role", employee_doc.custom_operations_role_allocation, ignore_permissions=True)
			except frappe.DoesNotExistError:
				 frappe.log_error(
					f"Invalid shift or operations role document for employee {employee_doc.name}",
					"Employee Schedule Creation Error"
				)
				 continue


			for day_offset in range(total_days):
				current_date = add_days(target_month_start, day_offset)
				availability = determine_availability(
					current_date,
					target_month_start, 
					total_days,
					employee_doc.day_off_category,
					employee_doc.number_of_days_off
				)
				create_or_update_schedule_for_employee(employee_doc, current_date, availability, operations_shift_doc, operations_role_doc)
		frappe.db.commit() # Commit once after processing all employees


def create_or_update_schedule_for_employee(employee, date_val, availability, operations_shift_doc, operations_role_doc):
	"""
	Create or update an Employee Schedule record for the given employee and date.
	"""
	try:
		date_str = cstr(date_val)
		name = f"{date_str}_{employee.name}_Basic"
		
		existing_schedule_name = frappe.get_value( 
			"Employee Schedule",
			{"employee": employee.name, "date": date_str},
			"name"
		)

		creation_ts = now() 
		owner_user = frappe.session.user 
		
		# Ensure start_time and end_time are valid time strings
		start_time_str = str(operations_shift_doc.start_time)
		end_time_str = str(operations_shift_doc.end_time)

		start_datetime = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M:%S")
		# Handle overnight shifts for end_datetime
		end_datetime_date_part = date_val
		if operations_shift_doc.start_time > operations_shift_doc.end_time: # Overnight shift
			end_datetime_date_part = add_days(date_val, 1)
		end_datetime = datetime.strptime(f"{cstr(end_datetime_date_part)} {end_time_str}", "%Y-%m-%d %H:%M:%S")

		day_off_ot = 1 if availability == "Day Off OT" else 0

		schedule_values = {
			"employee_availability": availability if availability != "Day Off OT" else "Working", # "Working" if Day Off OT
			"date": date_str,
			"shift": operations_shift_doc.name,
			"site": operations_shift_doc.site,
			"project": operations_shift_doc.project,
			"shift_type": operations_shift_doc.shift_type,
			"operations_role": operations_role_doc.name,
			"post_abbrv": operations_role_doc.post_abbrv,
			"roster_type": "Basic",
			"day_off_ot": day_off_ot,
			"start_datetime": start_datetime,
			"end_datetime": end_datetime,
			"owner": owner_user, 
			"modified_by": owner_user, 
			"creation": creation_ts,
			"modified": creation_ts 
		}

		if existing_schedule_name:
			frappe.db.set_value("Employee Schedule", existing_schedule_name, schedule_values)
		else:
			# Create a new record
			new_schedule_doc = frappe.new_doc("Employee Schedule")
			new_schedule_doc.name = name
			new_schedule_doc.employee = employee.name
			new_schedule_doc.employee_name = employee.employee_name
			new_schedule_doc.department = employee.department
			new_schedule_doc.update(schedule_values)
			new_schedule_doc.insert(ignore_permissions=True) 
			
	except Exception as e:
		frappe.log_error(f"Error for employee {employee.name} on {date_str}: {str(e)} \nTraceback: {frappe.get_traceback()}", "Employee Schedule Error")


def determine_availability(current_date, start_date, total_days, day_off_category, num_days_off):
    """
    Determine the availability of an employee based on day-off category and number of days off.
    """
    if day_off_category == "Weekly":
        # Weekly schedule logic
        day_of_week = current_date.weekday()
        week_day_index = (day_of_week + 1) % 7  # Sunday = 0
        return "Working" if week_day_index < (7 - num_days_off) else "Day Off OT"

    elif day_off_category == "Monthly":
        # Monthly schedule logic
        day_index = date_diff(current_date, start_date)
        return "Working" if day_index < total_days - num_days_off else "Day Off OT"

    return "Working"  # Default to working if no category matches


@frappe.whitelist()
def get_employee_details(employee_id):
	try:
		employee = frappe.get_doc("Employee", employee_id)
		return {
			"project": employee.project,
			"site": employee.site,
			"shift": employee.shift,
			"custom_is_reliever": employee.custom_is_reliever,
			"custom_operations_role_allocation": employee.custom_operations_role_allocation
		}
	except frappe.DoesNotExistError:
		return {"error": f"Employee {employee_id} not found."}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Error fetching details for Employee {employee_id}")
		return {"error": str(e)}


@frappe.whitelist()
def bulk_employee_record_update(updates):
	"""
	Bulk update Employee records in Frappe.

	Args:
		updates (list | str): A list of dictionaries (or JSON string representation) 
							  containing employee update data. Each dictionary must 
							  include "name" (Employee ID/Name) and other fields to update.

	Returns:
		dict: Success message with number of records updated, and list of failures if any.
	"""
	if isinstance(updates, str): # Handle if updates is a JSON string
		try:
			updates = json.loads(updates)
		except json.JSONDecodeError:
			frappe.throw("Invalid JSON string format for updates.")

	if not isinstance(updates, list):
		frappe.throw("Invalid data format. Expected a list of updates.")

	updated_records_names = [] 
	failed_updates = []

	for update_data in updates:
		employee_name_to_update = update_data.pop("name", None) 
		if not employee_name_to_update:
			failed_updates.append({"reason": "Missing 'name' (Employee ID/Name) in update data.", "data": update_data})
			continue
		
		if not update_data: # Skip if no fields to update after popping name
			failed_updates.append({"employee": employee_name_to_update, "reason": "No fields provided for update."})
			continue


		try:
			frappe.db.set_value("Employee", employee_name_to_update, update_data)
			updated_records_names.append(employee_name_to_update)
		except Exception as e:
			frappe.log_error(f"Failed to update Employee {employee_name_to_update}: {str(e)} \nTraceback: {frappe.get_traceback()}", "Bulk Employee Update Error")
			failed_updates.append({"employee": employee_name_to_update, "reason": str(e)})

	if updated_records_names: # Only commit if successful updates occurred
		frappe.db.commit()

	return {
		"message": f"Successfully updated {len(updated_records_names)} employee(s). Failures: {len(failed_updates)}.",
		"updated_employees": updated_records_names,
		"failed_updates": failed_updates
	}