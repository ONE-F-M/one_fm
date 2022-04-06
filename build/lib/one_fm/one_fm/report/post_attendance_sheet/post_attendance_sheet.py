# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate
from frappe import msgprint, _
from calendar import monthrange
import datetime

status_map = {
	"Absent": "A",
	"Half Day": "HD",
	"Holiday": "<b>H</b>",
	"Weekly Off": "<b>WO</b>",
	"On Leave": "L",
	"Present": "P",
	"Work From Home": "WFH",
    "Unmarked": "-"
	}

day_abbr = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]

def execute(filters=None):
	if not filters: filters = {}

	if filters.hide_year_field == 1:
		filters.year = 2020

	conditions, filters = get_conditions(filters)
	columns, days = get_columns(filters)
	if filters.group_by == "Post Type":
		att_map = get_attendance_list_post(conditions, filters)
		#print(att_map)
	else:
		att_map = get_attendance_list(conditions, filters)

	#print(att_map)  
	if not att_map:
		return columns, [], None, None

	if filters.group_by:
		if filters.group_by == "Post Type":
		    emp_map, group_by_parameters = get_employee_details_post(filters.company,filters["month"],filters["year"])
		else:
		    emp_map, group_by_parameters = get_employee_details(filters.group_by, filters.company)
		holiday_list = []
		for parameter in group_by_parameters:
			h_list = [emp_map[parameter][d]["holiday_list"] for d in emp_map[parameter] if emp_map[parameter][d]["holiday_list"]]
			holiday_list += h_list
	else:
		emp_map = get_employee_details(filters.group_by, filters.company)
		holiday_list = [emp_map[d]["holiday_list"] for d in emp_map if emp_map[d]["holiday_list"]]

	#print(emp_map)
	default_holiday_list = frappe.get_cached_value('Company',  filters.get("company"),  "default_holiday_list")
	holiday_list.append(default_holiday_list)
	holiday_list = list(set(holiday_list))
	holiday_map = get_holiday(holiday_list, filters["month"])

	data = []

	leave_list = None
	if filters.summarized_view:
		leave_types = frappe.db.sql("""select name from `tabLeave Type`""", as_list=True)
		leave_list = [d[0] + ":Float:120" for d in leave_types]
		columns.extend(leave_list)
		columns.extend([_("Total Late Entries") + ":Float:120", _("Total Early Exits") + ":Float:120"])

	if filters.group_by:
		emp_att_map = {}
		for parameter in group_by_parameters:
			emp_map_set = set([key for key in emp_map[parameter].keys()])
			att_map_set = set([key for key in att_map.keys()])
			if (att_map_set & emp_map_set):
				parameter_row = ["<b>"+ parameter + "</b>"] + ['' for day in range(filters["total_days_in_month"] + 2)]
				data.append(parameter_row)
				#print(emp_map[parameter])
				if filters.group_by == "Post Type":
				    record, emp_att_data = add_data_post(parameter , emp_map[parameter], att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=leave_list)
				else:
				    record, emp_att_data = add_data(emp_map[parameter], att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=leave_list)
				emp_att_map.update(emp_att_data)
				data += record
	else:
		record, emp_att_map = add_data(emp_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=leave_list)
		data += record
	#print(data)
	chart_data = get_chart_data(emp_att_map, days)

	return columns, data, None, chart_data

def get_chart_data(emp_att_map, days):
	labels = []
	datasets = [
		{"name": "Absent", "values": []},
		{"name": "Present", "values": []},
		{"name": "Leave", "values": []},
	]
	for idx, day in enumerate(days, start=0):
		p = day.replace("::65", "")
		labels.append(day.replace("::65", ""))
		total_absent_on_day = 0
		total_leave_on_day = 0
		total_present_on_day = 0
		total_holiday = 0
		for emp in emp_att_map.keys():
			if emp_att_map[emp][idx]:
				if emp_att_map[emp][idx] == "A":
					total_absent_on_day += 1
				if emp_att_map[emp][idx] in ["P", "WFH"]:
					total_present_on_day += 1
				if emp_att_map[emp][idx] == "HD":
					total_present_on_day += 0.5
					total_leave_on_day += 0.5
				if emp_att_map[emp][idx] == "L":
					total_leave_on_day += 1


		datasets[0]["values"].append(total_absent_on_day)
		datasets[1]["values"].append(total_present_on_day)
		datasets[2]["values"].append(total_leave_on_day)


	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}

	chart["type"] = "line"

	return chart
def get_day_off(employee,filters):
	#{'HR-EMP-00002': {1: ['Absent', None]}, 'HR-EMP-00003': {3: ['Present', 'ERPNext Developer']}}
	day_off_list = frappe.get_all("Employee Schedule", {"date":['between', (filters["start_date"], filters["end_date"])],"employee_availability":"Day Off", "employee":employee},["date"])
	lists={}
	for day_off in day_off_list:
		dates = day_off.date
		day = int(dates.strftime("%d"))
		lists.setdefault(employee, frappe._dict()).setdefault(day, "")
		lists[employee][day] = "Weekly Off"
	return(lists)

def add_data_post(parameter, employee_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=None):

	record = []
	emp_att_map = {}
	for emp in employee_map:
		emp_det = employee_map.get(emp)
		if not emp_det or emp not in att_map:
			continue

		row = []
		if filters.group_by:
			row += [" "]
		row += [emp, emp_det.employee_name]

		total_p = total_a = total_l = total_h = total_um= 0.0
		emp_status_map = []
		day_off = get_day_off(emp,filters)
		for day in range(filters["total_days_in_month"]):
			status = None
			if att_map.get(emp).get(day + 1):
				if att_map.get(emp).get(day + 1)[1] == parameter:
				    status = att_map.get(emp).get(day + 1)[0]
			else:
				if day_off:
				    status = day_off.get(emp).get(day + 1)
				if not status:
				    status = "Unmarked"

			if status is None and holiday_map:
				emp_holiday_list = emp_det.holiday_list if emp_det.holiday_list else default_holiday_list

				if emp_holiday_list in holiday_map:
					for idx, ele in enumerate(holiday_map[emp_holiday_list]):
						if day+1 == holiday_map[emp_holiday_list][idx][0]:
							if holiday_map[emp_holiday_list][idx][1]:
								status = "Weekly Off"
							else:
								status = "Holiday"
							total_h += 1

			abbr = status_map.get(status, "")
			emp_status_map.append(abbr)

			if  filters.summarized_view:
				if status == "Present" or status == "Work From Home":
					total_p += 1
				elif status == "Absent":
					total_a += 1
				elif status == "On Leave":
					total_l += 1
				elif status == "Half Day":
					total_p += 0.5
					total_a += 0.5
					total_l += 0.5
				elif not status:
					total_um += 1

		if not filters.summarized_view:
			row += emp_status_map

		if filters.summarized_view:
			row += [total_p, total_l, total_a, total_h, total_um]

		if not filters.get("employee"):
			filters.update({"employee": emp})
			conditions += " and employee = %(employee)s"
		elif not filters.get("employee") == emp:
			filters.update({"employee": emp})

		if filters.summarized_view:
			leave_details = frappe.db.sql("""select leave_type, status, count(*) as count from `tabAttendance`\
				where leave_type is not NULL %s group by leave_type, status""" % conditions, filters, as_dict=1)

			time_default_counts = frappe.db.sql("""select (select count(*) from `tabAttendance` where \
				late_entry = 1 %s) as late_entry_count, (select count(*) from tabAttendance where \
				early_exit = 1 %s) as early_exit_count""" % (conditions, conditions), filters)

			leaves = {}
			for d in leave_details:
				if d.status == "Half Day":
					d.count = d.count * 0.5
				if d.leave_type in leaves:
					leaves[d.leave_type] += d.count
				else:
					leaves[d.leave_type] = d.count

			for d in leave_list:
				if d in leaves:
					row.append(leaves[d])
				else:
					row.append("0.0")

			row.extend([time_default_counts[0][0],time_default_counts[0][1]])
		emp_att_map[emp] = emp_status_map
		record.append(row)

	return record, emp_att_map


def add_data(employee_map, att_map, filters, holiday_map, conditions, default_holiday_list, leave_list=None):

	record = []
	emp_att_map = {}
	for emp in employee_map:
		emp_det = employee_map.get(emp)
		if not emp_det or emp not in att_map:
			continue

		row = []
		if filters.group_by:
			row += [" "]
		row += [emp, emp_det.employee_name]

		total_p = total_a = total_l = total_h = total_um= 0.0
		emp_status_map = []
		day_off = get_day_off(emp,filters)
		for day in range(filters["total_days_in_month"]):
			status = None
			status = att_map.get(emp).get(day + 1)
			if not status:
				if day_off:
				    status = day_off.get(emp).get(day + 1)
				if not status:
				    status = "Unmarked"

			if status is None and holiday_map:
				emp_holiday_list = emp_det.holiday_list if emp_det.holiday_list else default_holiday_list

				if emp_holiday_list in holiday_map:
					for idx, ele in enumerate(holiday_map[emp_holiday_list]):
						if day+1 == holiday_map[emp_holiday_list][idx][0]:
							if holiday_map[emp_holiday_list][idx][1]:
								status = "Weekly Off"
							else:
								status = "Holiday"
							total_h += 1

			abbr = status_map.get(status, "")
			emp_status_map.append(abbr)

			if  filters.summarized_view:
				if status == "Present" or status == "Work From Home":
					total_p += 1
				elif status == "Absent":
					total_a += 1
				elif status == "On Leave":
					total_l += 1
				elif status == "Half Day":
					total_p += 0.5
					total_a += 0.5
					total_l += 0.5
				elif not status:
					total_um += 1

		if not filters.summarized_view:
			row += emp_status_map

		if filters.summarized_view:
			row += [total_p, total_l, total_a, total_h, total_um]

		if not filters.get("employee"):
			filters.update({"employee": emp})
			conditions += " and employee = %(employee)s"
		elif not filters.get("employee") == emp:
			filters.update({"employee": emp})

		if filters.summarized_view:
			leave_details = frappe.db.sql("""select leave_type, status, count(*) as count from `tabAttendance`\
				where leave_type is not NULL %s group by leave_type, status""" % conditions, filters, as_dict=1)

			time_default_counts = frappe.db.sql("""select (select count(*) from `tabAttendance` where \
				late_entry = 1 %s) as late_entry_count, (select count(*) from tabAttendance where \
				early_exit = 1 %s) as early_exit_count""" % (conditions, conditions), filters)

			leaves = {}
			for d in leave_details:
				if d.status == "Half Day":
					d.count = d.count * 0.5
				if d.leave_type in leaves:
					leaves[d.leave_type] += d.count
				else:
					leaves[d.leave_type] = d.count

			for d in leave_list:
				if d in leaves:
					row.append(leaves[d])
				else:
					row.append("0.0")

			row.extend([time_default_counts[0][0],time_default_counts[0][1]])
		emp_att_map[emp] = emp_status_map
		record.append(row)

	return record, emp_att_map

def get_columns(filters):
	columns = []

	if filters.group_by:
		columns = [_(filters.group_by)+ ":Link/Branch:120"]

	columns += [
		_("Employee") + ":Link/Employee:120", _("Employee Name") + ":Data/:120"
	]
	days = []
	for day in range(filters["total_days_in_month"]):
		date = str(filters.year) + "-" + str(filters.month)+ "-" + str(day+1)
		day_name = day_abbr[getdate(date).weekday()]
		days.append(cstr(day+1)+ " " +day_name +"::65")
	if not filters.summarized_view:
		columns += days

	if filters.summarized_view:
		columns += [_("Total Present") + ":Float:120", _("Total Leaves") + ":Float:120",  _("Total Absent") + ":Float:120", _("Total Holidays") + ":Float:120", _("Unmarked Days")+ ":Float:120"]
	return columns, days

def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql("""select employee, day(attendance_date) as day_of_month,
		status from tabAttendance where docstatus = 1 %s order by employee, attendance_date""" %
		conditions, filters, as_dict=1)
	if not attendance_list:
		msgprint(_("No attendance record found"), alert=True, indicator="orange")
	#print(attendance_list)
	att_map = {}

	for d in attendance_list:
		att_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, "")
		att_map[d.employee][d.day_of_month] = d.status

	return att_map

def get_attendance_list_post(conditions, filters):
	attendance_list = frappe.db.sql("""select employee, day(attendance_date) as day_of_month,
		status, post_type from tabAttendance where docstatus = 1 %s order by employee, attendance_date""" %
		conditions, filters, as_dict=1)
	#print(attendance_list)
    
	if not attendance_list:
		msgprint(_("No attendance record found"), alert=True, indicator="orange")

	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, "")
		att_map[d.employee][d.day_of_month] = [d.status,d.post_type]            
	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["total_days_in_month"] = monthrange(cint(filters.year), cint(filters.month))[1]
	filters["start_date"] = datetime.date(int(filters["year"]), int(filters["month"]), 1)
	filters["end_date"] = datetime.date(int(filters["year"]), int(filters["month"]), int(filters["total_days_in_month"]))

	conditions = " and month(attendance_date) = %(month)s and year(attendance_date) = %(year)s"

	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"
	if filters.get("project"): conditions += " and project = %(project)s"

	return conditions, filters

def get_employee_details_post(company, month, year):
	group_by = "post_type"
	emp_map = {}

	employee_details = frappe.db.sql("""SELECT DISTINCT Emp.name, Emp.employee_name, Emp.designation, Emp.department, Emp.branch, Emp.company,
		Emp.holiday_list, At.post_type from `tabEmployee` Emp, `tabAttendance` At WHERE Emp.name = At.employee AND Emp.company = {company} AND month(attendance_date) = {month} and year(attendance_date) = {year}"""
		.format(company=frappe.db.escape(company),month=month,year=year), as_dict=1)
	group_by_parameters = []
	if group_by:
		group_by_parameters = list(set(detail.get(group_by, "") for detail in employee_details if detail.get(group_by, "")))
		for parameter in group_by_parameters:
				emp_map[parameter] = {}


	for d in employee_details:
		if group_by and len(group_by_parameters):
			if d.get(group_by, None):
				emp_map[d.get(group_by)][d.name] = d
		else:
			emp_map[d.name] = d
	#print(emp_map)  
	if not group_by:
		return emp_map
	else:
		return emp_map, group_by_parameters

def get_employee_details(group_by, company):
	emp_map = {}
	query = """select name, employee_name, designation, department, branch, company,
		holiday_list from `tabEmployee` where company = %s """ % frappe.db.escape(company)

	if group_by:
		group_by = group_by.lower()
		query += " order by " + group_by + " ASC"
	employee_details = frappe.db.sql(query , as_dict=1)

	group_by_parameters = []
	if group_by:
		group_by_parameters = list(set(detail.get(group_by, "") for detail in employee_details if detail.get(group_by, "")))
		for parameter in group_by_parameters:
				emp_map[parameter] = {}


	for d in employee_details:
		if group_by and len(group_by_parameters):
			if d.get(group_by, None):

				emp_map[d.get(group_by)][d.name] = d
		else:
			emp_map[d.name] = d

	if not group_by:
		return emp_map
	else:
		return emp_map, group_by_parameters

def get_holiday(holiday_list, month):
	holiday_map = frappe._dict()
	for d in holiday_list:
		if d:
			holiday_map.setdefault(d, frappe.db.sql('''select day(holiday_date), weekly_off from `tabHoliday`
				where parent=%s and month(holiday_date)=%s''', (d, month)))

	return holiday_map

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)