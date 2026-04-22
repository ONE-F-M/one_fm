import pandas as pd
import json
from distutils.util import strtobool
from collections import defaultdict
from pandas.core.indexes.datetimes import date_range
from datetime import datetime, timedelta, date
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
		 emp.project,opsite.site_supervisor_name as site_supervisor,opshift.supervisor_name as shift_supervisor, emp.custom_operations_role_allocation, emp.custom_is_reliever, emp.custom_is_weekend_reliever
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
		frappe.log_error(title="Employees for Roster View", message=frappe.get_traceback())


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
		frappe.log_error(title="get_roster_view Error", message=frappe.get_traceback())
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


def get_employee_leave_attendance(employees, start_date):
    """
    Returns a dict of employees and their corresponding attendance dates if it falls on or after the start date,
    including dates from approved Annual Leave applications (from_date >= start_date).
    """
    attendance_dict = {}
    # Get attendance marked as On Leave
    all_attendance = frappe.get_all(
        "Attendance",
        {
            "attendance_date": [">=", start_date],
            "employee": ["IN", employees],
            "docstatus": 1,
            "status": "On Leave"
        },
        ["attendance_date", "employee"]
    )
    for each in all_attendance:
        attendance_dict.setdefault(each.employee, []).append(each.attendance_date)

    # Get approved Annual Leave applications with from_date >= start_date
    leave_applications = frappe.get_all(
        "Leave Application",
        {
            "employee": ["IN", employees],
            "from_date": [">=", start_date],
            "leave_type": "Annual Leave",
            "status": "Approved"
        },
        ["employee", "from_date", "to_date"]
    )
    for leave in leave_applications:
        from_date = getdate(leave.from_date)
        to_date = getdate(leave.to_date)
        days_count = date_diff(to_date, from_date) + 1  # inclusive
        leave_days = [add_days(from_date, i) for i in range(days_count)]
        # Add leave days to attendance_dict, ensuring uniqueness
        if leave.employee in attendance_dict:
            attendance_dict[leave.employee].extend(leave_days)
            # Make unique
            attendance_dict[leave.employee] = list(sorted(set(attendance_dict[leave.employee])))
        else:
            attendance_dict[leave.employee] = leave_days

    return attendance_dict

@frappe.whitelist()
def schedule_overtime(employees, shift, operations_role,start_date,end_date=None, selected_days_only=0,project_end_date=None):
	try:
		employees = json.loads(employees)
		if not employees:
			frappe.throw("Employees must be selected.")

		employee_list = list({obj["employee"] for obj in employees})
		if cint(project_end_date) and not end_date:
			project = frappe.db.get_value("Operations Shift", shift, ["project"])
			if frappe.db.exists("Contracts", {"project": project}):
				contract, end_date_val = frappe.db.get_value("Contracts", {"project": project}, ["name", "end_date"])
				if not end_date_val:
					frappe.throw("Please set contract end date for contract: {contract}".format(contract=contract))
				else:
					end_date = end_date_val

		# extreme schedule
		extreme_schedule(employees=employees, start_date=start_date, end_date=end_date, shift=shift,
			operations_role=operations_role, otRoster="true", keep_days_off=0, day_off_ot=0,
			employee_list=employee_list
		)
		update_roster(key="roster_view")

		response("success", 200, {"message":"Successfully scheduled overtime for employees"})
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Schedule Overtime")
		response("error", 200, None, str(e))


@frappe.whitelist()
def schedule_staff(employees, shift, operations_role, otRoster, start_date, project_end_date, keep_days_off=0, keep_days_off_ot=0, day_off_ot=None, end_date=None, selected_days_only=0):
	try:
		_start_date = getdate(start_date)

		validation_logs = []
		day_off_ot_warning = ""
		if cint(day_off_ot):
			day_off_ot_allowed = frappe.db.get_value("Operations Shift", shift, "day_off_ot_allowed")
			if not day_off_ot_allowed:
				day_off_ot_warning = f"<br><br><b>Note:</b> This {shift} prohibits Day Off OT."

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

		elif not end_date and not cint(project_end_date) and cint(selected_days_only):
			# If no end date and no project end date selected and selected_days_only is true
			employees_valid_dates = []
			for obj in employees:
				if getdate(obj.get("date")) not in employee_leave_attendance.get(obj.get("employee"),[]):
					employees_valid_dates.append({"employee": obj.get("employee"), "date": str(getdate(obj.get("date")))})
			employees = employees_valid_dates

		elif not cint(project_end_date) and not end_date and not cint(selected_days_only):
			end_date_val =  getdate(employees[-1].get("date")) if employees else get_last_day(getdate(start_date))
			employees = []
			list_of_date = date_range(start_date, end_date_val)
			for obj in employee_list:
				for day in list_of_date:
					if  day.date() not in employee_leave_attendance.get(obj,[]):
						employees.append({"employee": obj, "date": str(day.date())})
			end_date = end_date_val

		elif cint(project_end_date) and end_date:
			validation_logs.append("Please select either the project end date or set a custom date. You cannot set both!")

		emp_tuple = str(employee_list).replace("[", "(").replace("]",")")

		if "Projects Manager" not in user_roles and "Operations Manager" not in user_roles:
			all_employee_shift_query = frappe.db.sql("""
				SELECT DISTINCT es.shift, s.supervisor
				FROM `tabEmployee Schedule` es JOIN `tabOperations Shift` s ON es.shift = s.name
				WHERE
				es.date BETWEEN "{start_date}" AND "{end_date}"
				AND es.employee_availability="Working" AND es.employee IN {emp_tuple}
				GROUP BY es.shift
			""".format(start_date=start_date, end_date=end_date, emp_tuple=emp_tuple), as_dict=1)

		# Evaluate final acceptance conditions for creating Employee Schedule
		
		month_start = get_first_day(start_date)
		month_end = get_last_day(end_date)
		
		for obj in employee_list:
			rdo_count = frappe.db.count("Employee Schedule", filters={
				"employee": obj,
				"employee_availability": "Day Off",
				"date": ["between", [month_start, month_end]]
			})

			# Check if we are actively overwriting an existing Day Off
			# "When Employee Availability=Day Off and Keep Days Off is unchecked"
			obj_dates = [getdate(e.get("date")) for e in employees if e.get("employee") == obj]
			overwritten_rdo_count = 0
			if obj_dates:
				overwritten_rdo_count = frappe.db.count("Employee Schedule", filters={
					"employee": obj,
					"employee_availability": "Day Off",
					"date": ["in", obj_dates]
				})

			# Evaluate complex condition: Does Days after Joining Date or Days before Relieving Date
			# exceed Majority days AND Approved Leave=0 AND Total Rostered Day Offs=0?
			# Expanded: For overwriting, check if Total Rostered Day Offs <= 1.
			is_violating_rdo_policy = False
			if rdo_count == 0 or (rdo_count <= 1 and overwritten_rdo_count > 0 and not cint(keep_days_off)):
				emp_details = frappe.db.get_value("Employee", obj, ["date_of_joining", "relieving_date"], as_dict=True)
				if emp_details:
					month_days = date_diff(month_end, month_start) + 1
					majority_days = (month_days // 2) + 1
					
					doj = emp_details.get("date_of_joining")
					relieving_date = emp_details.get("relieving_date")
					
					days_after_joining = month_days
					if doj and getdate(doj) > month_start:
						if getdate(doj) <= month_end:
							days_after_joining = date_diff(month_end, getdate(doj)) + 1
						else:
							days_after_joining = 0
							
					days_before_relieving = month_days
					if relieving_date and getdate(relieving_date) < month_end:
						if getdate(relieving_date) >= month_start:
							days_before_relieving = date_diff(getdate(relieving_date), month_start) + 1
						else:
							days_before_relieving = 0
							
					exceeds_majority = (days_after_joining > majority_days) or (days_before_relieving > majority_days)
					
					leave_count = frappe.db.count("Leave Application", filters={
						"employee": obj,
						"leave_type": "Annual Leave",
						"status": "Approved",
						"from_date": ["<=", month_end],
						"to_date": [">=", month_start]
					})
					
					if exceeds_majority and (leave_count == 0):
						is_violating_rdo_policy = True				

			# Execute new overwrite condition check explicitly
			if overwritten_rdo_count > 0 and not cint(keep_days_off):
				if rdo_count <= 1 and is_violating_rdo_policy:
					validation_logs.append(f"<li><b>{obj}</b>'s total scheduled day off for this full calendar month will be less than 1. Please assign a day off before overwriting.</li>")

			pref = frappe.db.get_value("Employee", obj, "custom_day_off_preference")			
			if cint(day_off_ot) and pref == "Day Off":
				emp_name = frappe.db.get_value("Employee", obj, "employee_name") or obj
				obj_dates = [getdate(e.get("date")) for e in employees if e.get("employee") == obj]
				if obj_dates:
					from_date = min(obj_dates).strftime("%Y-%m-%d")
					to_date = max(obj_dates).strftime("%Y-%m-%d")
				else:
					from_date = getdate(start_date).strftime("%Y-%m-%d")
					to_date = getdate(end_date).strftime("%Y-%m-%d") if end_date else from_date
				
				import urllib.parse
				query_params = {
					"employee": obj,
					"employee_name": emp_name,
					"purpose": "Day Off Overtime",
					"from_date": from_date,
					"to_date": to_date,
					"status": "Draft"
				}
				link = "/app/shift-request/new?" + urllib.parse.urlencode(query_params)
				shift_req_link = f"<a href='{link}' target='_blank' style='text-decoration: underline; font-weight: bold;'>Shift Request</a>"
				
				validation_logs.append(f"<li><b>{obj}</b>'s Day Off Preference has been set as 'Day Off'. Please assign other employee or create {shift_req_link} for Day Off OT.</li>")

			if cint(day_off_ot) and pref == "Day Off OT":
				if rdo_count == 0 and is_violating_rdo_policy:
					validation_logs.append(f"<li><b>{obj}</b>'s total scheduled day off for this full calendar month is 0. Please assign a day off.</li>")


		if len(validation_logs) > 0:
			msg = "<ul style='padding-left: 20px;'>" + "".join([log if log.startswith("<li>") else f"<li>{log}</li>" for log in validation_logs]) + "</ul>"
			frappe.log_error(message=msg, title="Roster Schedule Validation")
			frappe.throw(msg, title="Roster Schedule")
		else:
			# extreme schedule
			extreme_schedule(employees=employees, start_date=start_date, end_date=end_date, shift=shift,
				operations_role=operations_role, otRoster=otRoster, keep_days_off=keep_days_off, keep_days_off_ot=keep_days_off_ot, day_off_ot=day_off_ot,
				employee_list=employee_list, day_off_ot_warning=day_off_ot_warning
			)
			update_roster(key="roster_view")

			response("success", 200, {"message":"Successfully rostered employees"})
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Schedule Roster")
		response("error", 200, None, str(e))

def update_roster(key):
	frappe.publish_realtime(key, "Success")


def extreme_schedule(employees, shift, operations_role, otRoster, start_date, end_date, keep_days_off, day_off_ot,
	employee_list, selected_reliever=None, keep_days_off_ot=0, day_off_ot_warning=""):
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
		start_date_val = getdate(start_date)
        # Build a map of selected employees
		employee_set = list(set(i["employee"] for i in employees))
		new_employees = []
		for emp in employee_set:
			current = start_date_val
			while current <= end_date_val:
				new_employees.append({"employee": emp,"date": str(current)})
				current += timedelta(days=1)
		if new_employees:
			employees = new_employees.copy()


	# if keeps_days_off is checked
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

	# if keeps_days_off_ot is checked
	if cint(keep_days_off_ot):
		day_off_ot_list = frappe.db.get_list("Employee Schedule", filters={
			"employee": ["IN", [i["employee"] for i in employees]],
			"date": ["IN", [i["date"] for i in employees]],
			"roster_type": "Basic",
			"day_off_ot": 1
		}, fields=["employee", "date"])

		# Build a quick lookup map for (employee, date) → True if day_off_ot is set
		day_off_ot_map = {(i.employee, str(i.date)): True for i in day_off_ot_list}

		# Inject day_off_ot = 1 into employees if Basic schedule has it
		for i in employees:
			if day_off_ot_map.get((i["employee"], i["date"])):
				i["day_off_ot"] = 1

	employees_list_db = frappe.db.get_list("Employee", filters={"name": ["IN", employee_list]}, fields=["name", "employee_name", "department","date_of_joining", "relieving_date"], ignore_permissions=True)
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
			joining_date = getdate(employee_detail.get("date_of_joining"))
			current_date = getdate(i.get("date"))
			relieving_date = employee_detail.get("relieving_date")

			if joining_date <= current_date and (not relieving_date or current_date <= getdate(relieving_date)):
				if employees_date_dict.get(i["employee"]):
					employees_date_dict[i["employee"]].append({
						"date":i["date"],
						"start_datetime": datetime.strptime(f"{i['date']} {shift_start_time}", "%Y-%m-%d %H:%M:%S"), 
						"end_datetime":datetime.strptime(f"{add_days(i['date'], 1) if next_day else i['date']} {shift_end_time}", "%Y-%m-%d %H:%M:%S"),
						"day_off_ot": i.get("day_off_ot")
					})
				else:
					employees_date_dict[i["employee"]] =[{"date":i["date"], "start_datetime": datetime.strptime(f"{i['date']} {shift_start_time}", "%Y-%m-%d %H:%M:%S"), "end_datetime":datetime.strptime(f"{add_days(i['date'], 1) if next_day else i['date']} {shift_end_time}", "%Y-%m-%d %H:%M:%S")}]
		else:
			# Log or handle cases where employee details or date_of_joining is missing
			frappe.log_error(message=f"Employee {i.get('employee')} missing details or date_of_joining.", title="Extreme Schedule Data Prep")


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


	query = """
		INSERT INTO `tabEmployee Schedule` (`name`, `employee`, `employee_name`, `department`, `date`, `shift`, `site`, `project`, `shift_type`, `employee_availability`,
		`operations_role`, `post_abbrv`, `roster_type`, `day_off_ot`, `start_datetime`, `end_datetime`, `owner`, `modified_by`, `creation`, `modified`)
		VALUES
	"""
	can_create = False
	omitted_days = set()

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

			# For each date, check overfill status
			post_data = validate_overfilled_post([current_processing_date], operations_shift_doc.name, operations_role_doc.name)
			post_number = post_data.get("post_number", 0)
			schedule_data = post_data.get("schedule_dict", {})

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

			# if current_processing_date not in omitted_days:
			already_scheduled = int(schedule_data.get(current_processing_date, 0))
			num_to_add_this_day = daily_add_count[current_processing_date]

			if already_scheduled + num_to_add_this_day > post_number:
				omitted_days.add(current_processing_date)


			employee_doc = employees_dict.get(employee_name_iter)
			name = f"{datevalue['date']}_{employee_name_iter}_{roster_type}"
			day_off_ot_val = datevalue.get('day_off_ot') or day_off_ot  
			query_values.append(f"""
				(
					'{name}', '{employee_name_iter}', '{employee_doc.employee_name}', '{employee_doc.department}', '{datevalue['date']}', '{operations_shift_doc.name}',
					'{operations_shift_doc.site}', '{operations_shift_doc.project}', '{operations_shift_doc.shift_type}', 'Working',
					'{operations_role_doc.name}', '{operations_role_doc.post_abbrv}', '{roster_type}',
					{day_off_ot_val}, '{datevalue.get('start_datetime')}', '{datevalue.get('end_datetime')}', '{owner}', '{owner}', '{creation}', '{creation}'
				)""")
			can_create = True


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
		omitted_days_str = ", ".join(datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y") for date in sorted(set(omitted_days)))
		title = "This action has overfilled the post for the following dates."
		msg = f"""
		<b>Role: {operations_role_doc.post_abbrv}</b> ({operations_role_doc.name}) <br>
		<b>Shift:</b> {operations_shift_doc.name}<br>
		<b>Dates:</b> {omitted_days_str}
		{day_off_ot_warning}
		"""
		frappe.msgprint(_(msg), _(title))
	elif day_off_ot_warning:
		frappe.msgprint(_(day_off_ot_warning.replace("<br><br><b>Note:</b> ", "")), _("Day Off OT Warning"))


	frappe.enqueue(update_employee_shift, employees=list(employees_date_dict.keys()), shift=shift, owner=owner, creation=creation)


def validate_overfilled_post(date_list_str, operations_shift_name, operations_role):
	cond = ""
	schedule_dict = {}
	base_query = f""" SELECT date ,count(name) as schedule_count from `tabEmployee Schedule`  WHERE shift = "{operations_shift_name}" and employee_availability = "Working" """
	post_number_res = frappe.db.sql(f""" SELECT count(name) as post_number from `tabOperations Post` where status = 'Active' and site_shift = '{operations_shift_name}' and post_template = '{operations_role}' """,as_dict=1)
	post_number = post_number_res[0].get("post_number") if post_number_res else 0

	if not date_list_str: # Handle empty date list
		return { "schedule_dict": schedule_dict, "post_number": post_number }

	if len(date_list_str) == 1:
		cond = f" AND date = '{date_list_str[0]}'"
	elif len(date_list_str) > 1:
		# Correctly format tuple for SQL IN clause
		cond = f" AND date in {str(tuple(date_list_str))}"

	full_query = base_query + cond + " GROUP BY date" if cond else base_query + " GROUP BY date"

	schedule_number_res = frappe.db.sql(full_query,as_dict=1)
	for each_item in schedule_number_res:
		schedule_dict[each_item.get("date").strftime("%Y-%m-%d")] = each_item.schedule_count


	return { "schedule_dict": schedule_dict, "post_number": post_number }

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
		frappe.log_error(message=frappe.get_traceback(), title="Schedule Leave Error")
		response("error", 500, None, str(e))


@frappe.whitelist(allow_guest=True)
def unschedule_staff(employees, roster_type, start_date=None, end_date=None, never_end=0, selected_days_only=0):
	try:
		_start_date = getdate(start_date) if start_date else None
		stop_date = getdate(end_date) if end_date else None

		employees = json.loads(employees)
		employee_list = list({obj["employee"] for obj in employees})

		if not employees:
			response("Error", 400, None, {"message": "Employees must be selected."})

		if not selected_days_only and not _start_date:
			frappe.throw("Must provide a start date if selected days are not targetted")

		if _start_date:
			employees = [i for i in employees if getdate(i["date"])>=_start_date]

		if end_date:
			end_date_val = getdate(end_date)
			employees = []
			list_of_date = date_range(start_date, end_date_val)
			for obj in employee_list:
				for day in list_of_date:
					employees.append({"employee": obj, "date": str(day.date())})
			end_date = end_date_val

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

		if not args.plan_end_date and not cint(args.project_end_date) and not cint(args.selected_days_only):
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
	
	elif args.post_status == "Client Post Off":
		if args.repeat_till and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and custom end date!"))
		
		if args.repeat not in ["Does not repeat", "Selected Days Only"] and not args.repeat_till and not cint(args.project_end_date):
			frappe.throw(_("Please set an end date!"))
		
		if args.repeat == "Does not repeat" and cint(args.project_end_date):
			frappe.throw(_("Cannot set both project end date and choose 'Does not repeat' option!"))
		
		client_post_off(posts, args)
		return response("Success", 200, {"message": "Client Post Off Marked Successfully"})

	frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long", timeout=3600)
	return response("Success", 200, {"message": "Your request is being processed in the background."})


def client_post_off(posts, args):
    """ This function sets the post status to Client Post Off by updating existing records """
    
    posts_list = json.loads(posts)
    
    # Extract unique posts
    unique_posts_list = list(set(post["post"] for post in posts_list))
    
    # Post wise dates mapping
    post_wise_dates = defaultdict(list)
    for post in posts_list:
        post_wise_dates[post["post"]].append(pd.to_datetime(post["date"]))
    
    # Fetch all projects linked to posts
    post_projects = get_post_porjects(unique_posts_list)
    
    # Use the same end date logic as post_off
    end_date_val = get_post_schedule_end_date(args, unique_posts_list, post_projects)
    
    if not end_date_val:
        frappe.throw(_("No end date specified."))
    
    # Collect all dates and posts for bulk processing
    existing_schedules = get_existing_post_schedules(args, end_date_val, unique_posts_list)
    
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
    
    # Get week days for Weekly repeat
    week_days = get_week_days(args) if args.repeat == "Weekly" else []
    if args.repeat == "Weekly" and not week_days:
        frappe.throw(_("Please select at least one weekday for weekly repetition."))
    
    insert_query = """
        Insert Into
            `tabPost Schedule`
            (
                `name`, `post`, `operations_role`, `post_abbrv`, `shift`, `site`,
                `project`, `date`, `post_status`, `owner`, `modified_by`, `creation`, `modified`
            )
        Values
    """
    query_values = []
    
    for post_name_iter in unique_posts_list:
        if previous_post != post_name_iter:
            previous_post = post_name_iter
            post_details_val = get_post_details(post_name_iter)
            if post_details_val:
                operations_role_val = post_details_val["post_template"]
                shift_val = post_details_val["site_shift"]
                post_abbrv_val = post_details_val["post_abbrv"]
                site_val = post_details_val["site"]
                project_detail_val = post_details_val["project"]
        
        # Handle different repeat patterns
        if args.repeat in ["Does not repeat", "Selected Days Only"]:
            dates_to_process = post_wise_dates.get(post_name_iter, [])
        else:
            # Select a non-empty start date for repeating patterns
            from_date = (
                args.get("client_post_off_from_date")
                or args.get("post_off_from_date")
                or args.get("plan_from_date")
            )
            if not from_date:
                frappe.throw(_("A valid start date is required to generate repeating schedules."))
            # Use appropriate frequency based on repeat type
            if args.repeat == "Monthly":
                dates_to_process = pd.date_range(start=from_date, end=end_date_val, freq="MS")
            elif args.repeat == "Yearly":
                dates_to_process = pd.date_range(start=from_date, end=end_date_val, freq="YS")
            else:
                # Default: generate daily dates (used for Weekly and other patterns)
                dates_to_process = pd.date_range(start=from_date, end=end_date_val)
        
        for date_item in dates_to_process:
            # Filter by weekday for Weekly repeat
            if args.repeat == "Weekly" and getdate(date_item).strftime("%A") not in week_days:
                continue 
            
            date_str = cstr(date_item.date()) if hasattr(date_item, 'date') else cstr(date_item)
            
            if (post_name_iter, date_str) in existing_schedules_set:
                delete_post_list.append(existing_schedules_set[(post_name_iter, date_str)])
            
            name = f"{post_name_iter}_{date_str}"
            query_values.append(f"""
                (
                    "{name}", "{post_name_iter}", "{operations_role_val}", "{post_abbrv_val}", "{shift_val}", "{site_val}",
                    "{project_detail_val}", "{date_str}", "Client Post Off", "{owner}", "{owner}", "{creation}", "{creation}"
                )""")
            insert_post_flag = True
    
    if insert_post_flag and query_values:
        insert_query += ",\n".join(query_values)
        
        insert_query += f"""
            On Duplicate Key Update
            modified_by = Values(modified_by),
            modified = "{creation}",
            operations_role = Values(operations_role),
            post_abbrv = Values(post_abbrv),
            shift = Values(shift),
            project = Values(project),
            site = Values(site),
            post_status = "Client Post Off",
            date= Values(date)
        """
        
        if delete_post_list:
            frappe.db.delete("Post Schedule", {"name": ["in", list(set(delete_post_list))]})
        frappe.db.sql(insert_query)
        frappe.db.commit()

def plan_post(posts, args):
	""" This function sets the post status to planned provided a post, start date and an end date """

	end_date_val = args.plan_end_date if args.plan_end_date and not cint(args.project_end_date) else None
	posts_list = json.loads(posts)

	# Extract unique posts
	unique_posts_list = list(set(post["post"] for post in posts_list))

	# Post wise dates mapping
	post_wise_dates = defaultdict(list)
	for post in posts_list:
		post_wise_dates[post["post"]].append(pd.to_datetime(post["date"]))

	# Fetch all projects linked to posts
	post_projects = {
		p["name"]: p["project"] for p in frappe.get_all(
			"Operations Post",
			filters={"name": ["in", unique_posts_list]},
			fields=["name", "project"]
		)
	}

	# If project_end_date is set, get contract end dates in bulk
	if cint(args.project_end_date) and not args.plan_end_date and not cint(args.selected_days_only):
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


	if not end_date_val and not cint(args.selected_days_only):
		frappe.throw(_("No end date specified."))

	# Collect all dates and posts for bulk processing
	existing_schedules = get_existing_post_schedules_for_plan_post(args, end_date_val, posts_list)

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

		dates_to_plan = post_wise_dates.get(post_name_iter2, []) if cint(args.selected_days_only) else pd.date_range(start=args.plan_from_date, end=end_date_val)

		for date_item in dates_to_plan:
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

def get_existing_post_schedules_for_plan_post(args, end_date, posts_list):
    # Extract unique posts
    unique_posts_list = list(set(post["post"] for post in posts_list))
    
    # Determine the from_date field based on the operation, with explicit fallback
    from_date = args.get("plan_from_date")
    if from_date in (None, ""):
        from_date = args.get("client_post_off_from_date")
    
    # Validate that a from_date value is provided
    if not from_date:
        frappe.throw(_("Either Plan From Date or Client Post Off From Date must be provided."))
    
    if cint(args.selected_days_only):
        schedules = []
        for post in posts_list:
            if frappe.db.exists("Post Schedule", {"post": post["post"], "date": post["date"]}):
                schedules.append(frappe.get_value("Post Schedule", {"post": post["post"], "date": post["date"]}, ["name", "post", "date"], as_dict=True))
        return schedules
    else:
        return frappe.get_all(
            "Post Schedule",
            filters={
                "date": ["between", [from_date, end_date]],
                "post": ["in", unique_posts_list]
            },
            fields=["name", "post", "date"]
        )

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

    from_date_for_logic = (
        args.client_post_off_from_date if "client_post_off_from_date" in args 
        else args.post_off_from_date if "post_off_from_date" in args 
        else args.plan_from_date
    )

    if args.repeat in ["Does not repeat", "Selected Days Only"]:
        end_date_val = get_last_day(from_date_for_logic)


    if cint(args.project_end_date) and post_projects and not args.repeat_till:
        project_names = list(post_projects.values())
        if project_names:
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
            else:
                if not args.repeat_till:
                    frappe.throw(_("No contract end dates found for associated projects, and no specific 'Repeat Till' date provided."))
        elif not args.repeat_till:
            frappe.throw(_("No projects to determine project end date, and no specific 'Repeat Till' date provided."))

    return end_date_val

def get_existing_post_schedules(args, end_date, unique_posts_list):
    if not unique_posts_list: 
        return []
    
    # Determine the from_date for the query using safe lookups and fallback
    from_date_for_query = args.get("plan_from_date")
    if from_date_for_query in (None, ""):
        from_date_for_query = args.get("client_post_off_from_date")
    if from_date_for_query in (None, ""):
        from_date_for_query = args.get("post_off_from_date")

    # Validate that a from_date value is provided for the query
    if not from_date_for_query:
        frappe.throw(_("A valid from date (Plan From Date, Client Post Off From Date, or Post Off From Date) must be provided."))
    
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
		frappe.log_error(message=frappe.get_traceback(), title="Error Deleting Post Schedules")

def check_day_off_preference_validation(employees, date_list, attempt_type="Day Off", is_update=False):
	"""
	Validates if an employee can be rostered for Day Off or Day Off OT based on their preference
	and current Rostered Day Off (RDO) count for the calendar months of the given dates.
	
	args:
		employees: list of employee names/dicts
		date_list: list of dates being scheduled
		attempt_type: 'Day Off' or 'Day Off OT'
		is_update: True if updating an existing schedule, False if creating new
	"""
	if not employees or not date_list:
		return

	# Normalize employees to a list of dicts with 'employee' and 'date'
	extracted_emps = []
	for emp in employees:
		if isinstance(emp, dict):
			extracted_emps.append(emp.get("employee"))
			if "date" in emp and emp["date"] not in date_list:
				date_list.append(getdate(emp["date"]))
		else:
			extracted_emps.append(emp)
			
	employee_names = list(set(extracted_emps))
	if not employee_names:
		return

	# Fetch preferences and dates for all employees in one go
	preferences = frappe.get_all(
		"Employee", 
		filters={"name": ["in", employee_names]}, 
		fields=["name", "employee_name", "custom_day_off_preference", "date_of_joining", "relieving_date"]
	)
	pref_map = {p.name: p for p in preferences}

	# Identify calendar months involved
	month_ranges = {}
	for d in date_list:
		dt = getdate(d)
		month_key = (dt.year, dt.month)
		if month_key not in month_ranges:
			month_ranges[month_key] = {"start": get_first_day(dt), "end": get_last_day(dt)}

	# Gather RDO count per employee per month
	errors = []
	for emp in employee_names:
		emp_data = pref_map.get(emp)
		if not emp_data:
			continue
		pref = emp_data.get("custom_day_off_preference")
		if not pref:
			continue # Optional: default behavior if no preference is set

		for month_key, m_range in month_ranges.items():
			month_start = m_range["start"]
			month_end = m_range["end"]
			
			# Get total RDO for this month
			rdo_count = frappe.db.count("Employee Schedule", filters={
				"employee": emp,
				"employee_availability": "Day Off",
				"date": ["between", [month_start, month_end]]
			})

			if pref == "Day Off":
				if attempt_type == "Day Off":
					pass # Allowed

			elif pref == "Day Off OT":
				if attempt_type == "Day Off":
					if rdo_count > 0:
						
						month_days = date_diff(month_end, month_start) + 1
						majority_days = (month_days // 2) + 1
						
						doj = emp_data.get("date_of_joining")
						relieving_date = emp_data.get("relieving_date")
						
						days_after_joining = month_days
						if doj and getdate(doj) > month_start:
							if getdate(doj) <= month_end:
								days_after_joining = date_diff(month_end, getdate(doj)) + 1
							else:
								days_after_joining = 0
								
						days_before_relieving = month_days
						if relieving_date and getdate(relieving_date) < month_end:
							if getdate(relieving_date) >= month_start:
								days_before_relieving = date_diff(getdate(relieving_date), month_start) + 1
							else:
								days_before_relieving = 0
								
						exceeds_majority = (days_after_joining > majority_days) or (days_before_relieving > majority_days)
						
						# Approved Annual Leave in this month
						leave_count = frappe.db.count("Leave Application", filters={
							"employee": emp,
							"leave_type": "Annual Leave",
							"status": "Approved",
							"from_date": ["<=", month_end],
							"to_date": [">=", month_start]
						})
						
						condition_met = exceeds_majority and (leave_count == 0) and (rdo_count == 0)
						
						if not condition_met:
							emp_name = emp_data.get("employee_name") or emp
							emp_dates = [getdate(e) for e in date_list if e]
							if emp_dates:
								from_date = min(emp_dates).strftime("%Y-%m-%d")
								to_date = max(emp_dates).strftime("%Y-%m-%d")
							else:
								from_date = getdate().strftime("%Y-%m-%d")
								to_date = getdate().strftime("%Y-%m-%d")
							
							import urllib.parse
							query_params = {
								"employee": emp,
								"employee_name": emp_name,
								"purpose": "Assign Day Off",
								"from_date": from_date,
								"to_date": to_date,
								"status": "Draft"
							}
							link = "/app/shift-request/new?" + urllib.parse.urlencode(query_params)
							shift_req_link = f"<a href='{link}' target='_blank' style='text-decoration: underline; font-weight: bold;'>Shift Request</a>"
							
							errors.append(f"<li><b>{emp}</b>'s Day Off Preference has been set as 'Day Off OT'. Please create {shift_req_link} for Day Off.</li>")

	if errors:
		msg = "<ul style='padding-left: 20px;'>" + "".join(errors) + "</ul>"
		frappe.throw(msg, title="Day Off Preference Validation Mismatch")
							
				
def check_client_day_off_eligibility(employee, date_str):
	"""
	Check whether an employee is eligible to receive a 'Client Day Off' on a given date.
	Eligibility requires that the mandatory Day Off quota has been fully rostered
	within the applicable period (weekly or monthly).

	Returns:
		(True, None)              – eligible, proceed with Client Day Off.
		(False, error_message)    – not eligible, surface error_message as msgprint.
	"""
	emp_data = frappe.db.get_value(
		"Employee", employee, ["day_off_category", "number_of_days_off"]
	)
	if not emp_data:
		return True, None
		
	day_off_category, number_of_days_off = emp_data

	if not day_off_category or not number_of_days_off:
		# No quota configured — allow Client Day Off
		return True, None

	number_of_days_off = cint(number_of_days_off)
	current_date = getdate(date_str)

	if day_off_category == "Monthly":
		period_start = get_first_day(current_date)
		period_end = get_last_day(current_date)
		error_msg = _("Total day off for this calendar month has not been utilized fully. Please assign a Day Off first.")
	else:  # Weekly
		# Week starts on Sunday: align using the same logic as get_week_start_end in utils.py
		week_day_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}  # Mon=0..Sun=6 → 1..0
		start_offset = week_day_map[current_date.weekday()]
		period_start = add_days(current_date, -start_offset)
		period_end = add_days(period_start, 6)
		error_msg = _("Total day off for this week has not been utilized fully. Please assign a Day Off first.")

	# Count existing 'Day Off' schedules in the period (excluding the current date being set)
	existing_day_offs = frappe.db.count(
		"Employee Schedule",
		{
			"employee": employee,
			"employee_availability": "Day Off",
			"date": ["between", [period_start, period_end]],
		}
	)

	if existing_day_offs >= number_of_days_off:
		return True, None

	return False, error_msg


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
		
		# Validate Day Off creation/update before proceeding
		validation_dates = []
		if cint(selected_dates):
			validation_dates = [emp["date"] for emp in json.loads(employees)]
		else:
			# If recurring, checking all dates could be expensive or complex upfront.
			# Let's check against the start dates at least, or ideally after gathering all target dates.
			pass # We will do a generic check or let the loop handle it
			
		# To accurately check, we need the full list of dates being processed for each employee.
		# We'll collect all dates into a dict of {employee: [dates]} to pass to validation.
		emp_date_map = frappe._dict()
		employees_list = json.loads(employees)

		if cint(selected_dates):
			for emp in employees_list:
				emp_date_map.setdefault(emp["employee"], []).append(emp["date"])
		else:
			effective_end_date = None
			if repeat_till and not cint(project_end_date):
				effective_end_date = getdate(repeat_till)
			for emp in employees_list:
				current_employee_date = getdate(emp["date"])
				# Resolve effective_end_date per employee if project_end_date is checked
				emp_end_date = effective_end_date
				if cint(project_end_date) and not (repeat_till and not cint(project_end_date)):
					project_val = frappe.db.get_value("Employee", emp["employee"], "project")
					if project_val and frappe.db.exists("Contracts", {"project": project_val}):
						contract, contract_end_date = frappe.db.get_value("Contracts", {"project": project_val}, ["name", "end_date"])
						if contract_end_date:
							emp_end_date = getdate(contract_end_date)

				if emp_end_date:
					if repeat and repeat_freq == "Weekly":
						for date_iter in pd.date_range(start=current_employee_date, end=emp_end_date):
							if getdate(date_iter).strftime("%A") in week_days and getdate(date_iter) > getdate(today()):
								emp_date_map.setdefault(emp["employee"], []).append(str(date_iter.date()))
					elif repeat and repeat_freq == "Monthly":
						for date_iter in month_range(current_employee_date, emp_end_date):
							if getdate(date_iter) > getdate(today()):
								emp_date_map.setdefault(emp["employee"], []).append(str(date_iter.date()))

		# Now validate all collected dates per employee
		for emp_mapped, dates_mapped in emp_date_map.items():
			check_day_off_preference_validation([emp_mapped], dates_mapped, attempt_type=employee_availability, is_update=False)

		if cint(selected_dates):
			for employee_item in employees_list:
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
					# --- Client Day Off eligibility check ---
					if cint(client_day_off):
						eligible, msg = check_client_day_off_eligibility(employee_item["employee"], date_val)
						if not eligible:
							emp_name = frappe.db.get_value("Employee", employee_item["employee"], "employee_name") or employee_item["employee"]
							frappe.msgprint(
								_("{0} ({1}) on {2}: {3}").format(emp_name, employee_item["employee"], date_val, msg),
								title=_("Client Day Off Warning"),
								indicator="orange"
							)
					# ----------------------------------------
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
							# --- Client Day Off eligibility check (Weekly repeat) ---
							if cint(client_day_off):
								eligible, msg = check_client_day_off_eligibility(employee_item["employee"], str(date_iter.date()))
								if not eligible:
									emp_name = frappe.db.get_value("Employee", employee_item["employee"], "employee_name") or employee_item["employee"]
									frappe.msgprint(
										_("{0} ({1}) on {2}: {3}").format(emp_name, employee_item["employee"], str(date_iter.date()), msg),
										title=_("Client Day Off Warning"),
										indicator="orange"
									)
							# ---------------------------------------------------------
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
							# --- Client Day Off eligibility check (Monthly repeat) ---
							if cint(client_day_off):
								eligible, msg = check_client_day_off_eligibility(employee_item["employee"], str(date_iter.date()))
								if not eligible:
									emp_name = frappe.db.get_value("Employee", employee_item["employee"], "employee_name") or employee_item["employee"]
									frappe.msgprint(
										_("{0} ({1}) on {2}: {3}").format(emp_name, employee_item["employee"], str(date_iter.date()), msg),
										title=_("Client Day Off Warning"),
										indicator="orange"
									)
							# ----------------------------------------------------------
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
			# NOTE: commit is deferred until reliever validation passes

		if selected_reliever:
			if frappe.db.exists("Employee", selected_reliever):
				reliever_roster_assignment(selected_reliever, roster_list)
			else:
				frappe.msgprint(f"Reliever with Employee ID {selected_reliever} not found.")

		# Commit only after all validations (including reliever) have passed
		frappe.db.commit()

		return response("success", 200, {"message":"Days Off set successfully."})
	except frappe.ValidationError as e:
		# Return as HTTP 200 so the JS callback fires and error_handler(res) shows the message.
		# HTTP 500 would route to the jQuery AJAX error handler, bypassing our callback entirely.
		frappe.db.rollback()
		return response("error", 200, None, str(e))
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(message=frappe.get_traceback(), title="Day Off Error")
		return response("error", 200, None, str(e))


def reliever_roster_assignment(reliver_emp_name, roster_list_arg):
	day_off_ot = 0
	keep_days_off = 0
	employee_list_for_extreme = [reliver_emp_name]
	otRoster = "false"
	
	# Validate that the reliever has at least 1 Day Off in the month, subject to new conditions
	emp_data = frappe.db.get_value("Employee", reliver_emp_name, ["employee_name", "date_of_joining", "relieving_date"], as_dict=True)
	if emp_data:
		joining_date = getdate(emp_data.get("date_of_joining")) if emp_data.get("date_of_joining") else None
		relieving_date = getdate(emp_data.get("relieving_date")) if emp_data.get("relieving_date") else None
		reliever_name = emp_data.get("employee_name") or reliver_emp_name
		
		months_checked = set()
		for roster_data_item in roster_list_arg:
			if roster_data_item and roster_data_item.get("date"):
				date_val_str = roster_data_item["date"].strftime("%Y-%m-%d") if isinstance(roster_data_item["date"], (datetime, pd.Timestamp)) else cstr(roster_data_item["date"])
				current_date = getdate(date_val_str)
				
				month_start = get_first_day(current_date)
				month_end = get_last_day(current_date)
				month_key = (month_start, month_end)
				
				if month_key not in months_checked:
					# 1. Total Rostered Day Offs = 0
					day_off_count = frappe.db.count("Employee Schedule", {
						"employee": reliver_emp_name,
						"employee_availability": "Day Off",
						"date": ["between", [month_start, month_end]]
					})
					
					# 2. Approved Annual Leave = 0
					annual_leave_count = frappe.db.count("Leave Application", {
						"employee": reliver_emp_name,
						"leave_type": "Annual Leave",
						"status": "Approved",
						"from_date": ["<=", month_end],
						"to_date": [">=", month_start]
					})
					
					# 3. Does Days after Joining Date or Days before Relieving Date exceed the Majority days of the Calendar Month?
					# Calculate the active period within this specific month
					active_start = max(month_start, joining_date) if joining_date else month_start
					active_end = min(month_end, relieving_date) if relieving_date else month_end
					
					active_days_in_month = date_diff(active_end, active_start) + 1
					total_days_in_month = date_diff(month_end, month_start) + 1
					majority_days = total_days_in_month / 2.0
					
					exceeds_majority = active_days_in_month > majority_days
					
					if day_off_count == 0 and annual_leave_count == 0 and exceeds_majority:
						raise frappe.ValidationError(_("{0} total scheduled day off for this full calender month is 0. Please assign a day off.").format(reliever_name))
					
					months_checked.add(month_key)

	for roster_data_item in roster_list_arg:
		if roster_data_item and roster_data_item.get("shift") and roster_data_item.get("operations_role") and \
		   roster_data_item.get("start_datetime") and roster_data_item.get("end_datetime") and roster_data_item.get("date"):

			shift_val = roster_data_item["shift"]
			operations_role_val = roster_data_item["operations_role"]

			# Ensure date is correctly formatted string YYYY-MM-DD
			date_val_str = roster_data_item["date"].strftime("%Y-%m-%d") if isinstance(roster_data_item["date"], (datetime, pd.Timestamp)) else cstr(roster_data_item["date"])

			employees_for_extreme = [{"employee":reliver_emp_name,"date":date_val_str}]

			# For reliever assignment, roster only for the specific day-off date
			# and do not expand to a date range based on start/end datetimes.
			extreme_schedule(
				employees=employees_for_extreme,
				shift=shift_val,
				operations_role=operations_role_val,
				otRoster=otRoster,
				start_date=date_val_str,
				end_date=None,
				keep_days_off=keep_days_off,
				day_off_ot=day_off_ot,
				employee_list=employee_list_for_extreme,
				selected_reliever=reliver_emp_name,
			)
		else:
			frappe.log_error(message=f"Skipping reliever assignment due to incomplete roster_data: {roster_data_item}", title="Reliever Assignment")


def get_shift_details_of_employee(emp_name_arg, date_arg):
	emp_project, emp_site, emp_shift, designation = frappe.db.get_value("Employee", emp_name_arg, ["project", "site", "shift", "designation"])
	if not emp_shift:
		frappe.log_error(message=f"Employee {emp_name_arg} has no default shift assigned.", title="Get Shift Details")
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
			frappe.log_error(message=f"No matching Operations Role for emp {emp_name_arg}, shift {emp_shift}, designation {designation}, project {emp_project}", title="Get Shift Details")
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
def assign_staff(employees, shift, custom_is_reliever, custom_is_weekend_reliever, custom_operations_role_allocation=None, request_employee_assignment=None):
	if not employees:
		frappe.throw("Please select employees first")

	shift_name_val, site_val, project_val = frappe.db.get_value("Operations Shift", shift, ["name", "site", "project"])

	try:
		employees_list_json = json.loads(employees)
		for employee_name_iter in employees_list_json:
			if not cint(request_employee_assignment):
				frappe.enqueue(assign_job, employee=employee_name_iter, shift=shift_name_val, site=site_val, project=project_val,
							   custom_operations_role_allocation=custom_operations_role_allocation,
							   custom_is_reliever=custom_is_reliever,
							   custom_is_weekend_reliever=custom_is_weekend_reliever, is_async=True, queue="long")
			else:
				emp_project_db, emp_site_db, emp_shift_db = frappe.db.get_value("Employee", employee_name_iter, ["project", "site", "shift"])

				if emp_project_db != project_val or emp_site_db != site_val or emp_shift_db != shift_name_val:
					frappe.enqueue(create_request_employee_assignment, employee=employee_name_iter,
								   from_shift=emp_shift_db, to_shift=shift_name_val, is_async=True, queue="long")

		frappe.enqueue(update_roster, key="staff_view", is_async=True, queue="long")
		return response("Success", 200, {"message": "Assignment request processed."})

	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Assign Staff Error")
		return response("Error", 500, None, str(e))


def create_request_employee_assignment(employee, from_shift, to_shift):
	req_ea_doc = frappe.new_doc("Request Employee Assignment")
	req_ea_doc.employee = employee
	req_ea_doc.from_shift = from_shift
	req_ea_doc.to_shift = to_shift
	req_ea_doc.save(ignore_permissions=True)
	frappe.db.commit()


def assign_job(employee, shift, site, project, custom_operations_role_allocation, custom_is_reliever, custom_is_weekend_reliever):
	update_values = {
		"shift": shift,
		"site": site,
		"project": project,
		"custom_operations_role_allocation": custom_operations_role_allocation,
		"custom_is_reliever": custom_is_reliever,
		"custom_is_weekend_reliever": custom_is_weekend_reliever
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
    today_date = getdate(nowdate())
    target_month_start = get_first_day(add_months(today_date, 1))
    target_month_end = get_last_day(add_months(today_date, 1))
    weeks = split_into_weeks_with_sunday_as_first_day(target_month_start, target_month_end)

    shifts_with_auto_roster = frappe.get_all(
        "Operations Shift",
        filters={"automate_roster": 1},
        fields=["name"]
    )
    shift_names = [shift["name"] for shift in shifts_with_auto_roster]

    if not shift_names:
        return

    employees = frappe.get_all(
        "Employee",
        filters={
            "shift": ["in", shift_names],
            "status": "Active"
        },
        fields=[
            "name", "employee_name", "department", "day_off_category", "number_of_days_off",
            "custom_operations_role_allocation", "shift", "date_of_joining", "relieving_date"
        ]
    )

    leave_dates_by_employee = get_leave_dates_by_employee_during_date_range(target_month_start, target_month_end)

    for emp in employees:
        if not emp.shift or not emp.custom_operations_role_allocation:
            frappe.log_error(
                message=f"Missing shift or operations role for employee {emp.name}",
                title="Employee Schedule Creation Error"
            )
            continue

        try:
            shift_doc = frappe.get_doc("Operations Shift", emp.shift, ignore_permissions=True)
            role_doc = frappe.get_doc("Operations Role", emp.custom_operations_role_allocation, ignore_permissions=True)
        except frappe.DoesNotExistError:
            frappe.log_error(
                message=f"Invalid shift or operations role for employee {emp.name}",
                title="Employee Schedule Creation Error"
            )
            continue

        leave_dates = set(map(getdate, leave_dates_by_employee.get(emp.name, [])))
        day_off_category = emp.day_off_category
        num_days_off = emp.number_of_days_off or 0

        if day_off_category == "Weekly":
            for week in weeks:
                process_schedule_range(emp, week["start"], week["end"], leave_dates, num_days_off, day_off_category, shift_doc, role_doc)

        elif day_off_category == "Monthly":
            process_schedule_range(emp, target_month_start, target_month_end, leave_dates, num_days_off, day_off_category, shift_doc, role_doc)

    frappe.db.commit()


def process_schedule_range(emp, range_start, range_end, leave_dates, num_days_off, day_off_category, shift_doc, role_doc):
    start_date = max(range_start, emp.date_of_joining or date.min)
    end_date = min(range_end, emp.relieving_date or date.max)

    total_days_in_range = date_diff(get_last_day(end_date), get_first_day(start_date)) + 1 if day_off_category == "Monthly" else 7 # total days in month/week
    active_days = date_diff(end_date, start_date) + 1 # active days within the company considering joining/relieving date
    leave_in_range = {d for d in leave_dates if start_date <= d <= end_date}

    actual_working_days = active_days - len(leave_in_range)
	
    if actual_working_days <= 0:
        return
	
    calculated_no_of_days_off = round(actual_working_days / total_days_in_range * num_days_off)

    for day_offset in range(active_days):
        current_date = add_days(start_date, day_offset)
        if current_date in leave_in_range:
            continue

        availability = determine_availability(
            current_date,
            start_date,
            active_days,
            day_off_category,
            calculated_no_of_days_off
        )

        create_or_update_schedule_for_employee(emp, current_date, availability, shift_doc, role_doc)


def create_or_update_schedule_for_employee(employee, date_val, availability, operations_shift_doc, operations_role_doc):
	"""
	Create or update an Employee Schedule record for the given employee and date.
	"""
	try:
		date_str = cstr(date_val)
		name = f"{date_str}_{employee.name}_Basic"

		existing_schedule_name = frappe.get_value(
			"Employee Schedule",
			{"employee": employee.name, "date": date_str, "roster_type": "Basic", "shift_type": operations_shift_doc.shift_type},
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
		frappe.log_error(message=f"Error for employee {employee.name} on {date_str}: {str(e)} \nTraceback: {frappe.get_traceback()}", title="Employee Schedule Error")

def get_leave_dates_by_employee_during_date_range(start_date, end_date):
    leave_applications = frappe.db.sql("""
        SELECT employee, from_date, to_date
        FROM `tabLeave Application`
        WHERE leave_type IN ('Annual Leave', 'Leave Without Pay')
		AND status = 'Approved'
        AND (
            (from_date <= %(end_date)s)
            AND
            (to_date >= %(start_date)s)
        )
    """, { "start_date": start_date, "end_date": end_date }, as_dict=True)

    leave_dates_by_employee = {}

    for row in leave_applications:
        employee = row.employee
        from_date = getdate(row.from_date)
        to_date = getdate(row.to_date)
        
        days_count = date_diff(to_date, from_date) + 1  # inclusive
        leave_days = [(add_days(from_date, i)) for i in range(days_count)]

        if employee not in leave_dates_by_employee:
            leave_dates_by_employee[employee] = set()

        leave_dates_by_employee[employee].update(leave_days)

    return leave_dates_by_employee

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

def split_into_weeks_with_sunday_as_first_day(start_date, end_date):
    """
    Splits a given date range into weeks, with each week starting on Sunday.

    Args:
        start_date (str or datetime.date): The starting date of the range.
        end_date (str or datetime.date): The ending date of the range.

    Returns:
        list[dict]: A list of dictionaries, each containing:
            - "start" (datetime.date): Start date of the week (clipped to `start_date` if necessary).
            - "end" (datetime.date): End date of the week (clipped to `end_date` if necessary).
    """
    start = getdate(start_date)
    end = getdate(end_date)

    weekday = start.weekday()  # Monday=0 ... Sunday=6
    days_to_sunday = (weekday + 1) % 7
    start_sunday = add_days(start, -days_to_sunday)

    week_ranges = []

    current = start_sunday
    while current <= end:
        week_start = current
        week_end = add_days(week_start, 6)

        actual_start = max(week_start, start)
        actual_end = min(week_end, end)

        week_ranges.append({
            "start": getdate(actual_start),
            "end": getdate(actual_end)
        })

        current = add_days(week_end, 1)

    return week_ranges


@frappe.whitelist()
def get_employee_details(employee_id):
	try:
		employee = frappe.get_doc("Employee", employee_id)
		return {
			"project": employee.project,
			"site": employee.site,
			"shift": employee.shift,
			"custom_is_reliever": employee.custom_is_reliever,
			"custom_is_weekend_reliever": employee.custom_is_weekend_reliever,
			"custom_operations_role_allocation": employee.custom_operations_role_allocation
		}
	except frappe.DoesNotExistError:
		return {"error": f"Employee {employee_id} not found."}
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title=f"Error fetching details for Employee {employee_id}")
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
			frappe.log_error(message=f"Failed to update Employee {employee_name_to_update}: {str(e)} \nTraceback: {frappe.get_traceback()}", title="Bulk Employee Update Error")
			failed_updates.append({"employee": employee_name_to_update, "reason": str(e)})

	if updated_records_names: # Only commit if successful updates occurred
		frappe.db.commit()

	return {
		"message": f"Successfully updated {len(updated_records_names)} employee(s). Failures: {len(failed_updates)}.",
		"updated_employees": updated_records_names,
		"failed_updates": failed_updates
	}


@frappe.whitelist()
def get_all_projects():
    return frappe.get_list(
        "Project",
        filters={"custom_exclude_from_default_shift_checker": ["!=", 1]},
        fields=["name"],
        limit_page_length=1000
    )

@frappe.whitelist()
def suspend_employee_action(employees, selected_dates=0, repeat=0, repeat_freq=None, repeat_till=None, project_end_date=0, week_days=None):
	from dateutil.relativedelta import relativedelta
	try:
		employees = json.loads(employees)
		if week_days:
			week_days = json.loads(week_days)
		
		for employee_item in employees:
			emp_name = employee_item["employee"]
			base_date = getdate(employee_item["date"])
			
			if cint(selected_dates):
				target_dates = [base_date]
			else:
				# Find end date
				if cint(project_end_date):
					proj = frappe.db.get_value("Employee", emp_name, "project")
					if proj:
						end_date = frappe.db.get_value("Project", proj, "expected_end_date")
					if not proj or not end_date:
						end_date = get_last_day(base_date) # Fallback to end of month
				elif repeat_till:
					end_date = getdate(repeat_till)
				else:
					end_date = base_date
				
				target_dates = []
				if repeat_freq == "Weekly" and week_days:
					for date_item in pd.date_range(start=base_date, end=end_date):
						if date_item.strftime("%A") in week_days:
							target_dates.append(date_item.date())
				elif repeat_freq == "Monthly":
					current_date = base_date
					while current_date <= getdate(end_date):
						target_dates.append(current_date)
						current_date = current_date + relativedelta(months=1)
				else:
					target_dates = [base_date]

			for target_date in target_dates:
				date_str = str(target_date)
				sch = frappe.db.get_value("Employee Schedule", {"employee": emp_name, "date": date_str, "roster_type": "Basic"}, "name")
				if sch:
					doc = frappe.get_doc("Employee Schedule", sch)
					doc.employee_availability = "Suspended"
					doc.save(ignore_permissions=True)
				else:
					emp_doc = frappe.get_doc("Employee", emp_name)
					doc = frappe.new_doc("Employee Schedule")
					doc.employee = emp_name
					doc.employee_name = emp_doc.employee_name
					doc.department = emp_doc.department
					doc.date = date_str
					doc.employee_availability = "Suspended"
					doc.roster_type = "Basic"
					doc.start_datetime = f"{date_str} 00:00:00"
					doc.end_datetime = f"{date_str} 23:59:59"
					doc.insert(ignore_permissions=True)
		frappe.db.commit()
		response("Success", 200, {"message": "Suspension logic scheduled successfully."})
	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Suspend Employee Error")
		response("Error", 200, None, str(e))