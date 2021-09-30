# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, cint, getdate, add_to_date
from calendar import monthrange
import pandas as pd

employees_not_rostered = set()

def execute(filters=None):
	global employees_not_rostered
	employees_not_rostered.clear()
	if filters:
		days_in_month = monthrange(cint(filters.year), cint(filters.month))[1]
		filters["start_date"] = filters.year + "-" + filters.month + "-" + "1"
		filters["end_date"] = add_to_date(filters["start_date"], days = days_in_month-1)
	columns = get_columns(filters) 
	data, chart_data = get_data(filters)
	return columns, data, None, chart_data

def get_columns(filters):
	return [
		_("Date") + ":Date:150",
		_("Active Employees") + ":Int:150",
		_("Employees Rostered") + ":Int:250",
		_("Employees Not Rostered") + ":Int:250",
		_("Employees On Day Off/Leave") + ":Int:250",
		_("Result") + ":Data:150"
	]	


def get_data(filters=None):
	data = []
	labels = []
	datasets = [
		{"name": "Active Employees\n\n\n", "values": []},
		{"name": "Employees Rostered\n\n\n", "values": []},
		{"name": "Employees Not Rostered\n\n\n", "values": []},
		{"name": "Employees on Day Off/Leave\n\n\n", "values": []},
	]
	chart = {}
	if filters:
		for date in pd.date_range(start=filters["start_date"], end=filters["end_date"]):
			employee_list = get_active_employees(date)		
			rostered_employees = get_working_employees(date)
			employees_on_day_off_leave = get_not_working_employees(date)

			employee_not_rostered_count = 0

			for employee in employee_list:
				if not frappe.db.exists({'doctype': 'Employee Schedule', 'date': date, 'employee': employee.employee}):
					global employees_not_rostered
					employees_not_rostered.add(employee.employee + ": " + get_employee_name(employee.employee))
					employee_not_rostered_count = employee_not_rostered_count + 1

			result = "OK"
			if employee_not_rostered_count > 0:
				result = "NOT OK"

			row = [
				cstr(date).split(" ")[0],
				len(employee_list),
				len(rostered_employees),
				employee_not_rostered_count,
				len(employees_on_day_off_leave),
				result			
			]

			data.append(row)

			labels.append("...")
			datasets[0]["values"].append(len(employee_list))
			datasets[1]["values"].append(len(rostered_employees))
			datasets[2]["values"].append(employee_not_rostered_count)
			datasets[3]["values"].append(len(employees_on_day_off_leave))

		chart = {
			"data": {
				"labels": labels,
				"datasets": datasets
			}
		}

		chart["type"] = "line"

	return data, chart

def get_active_employees(date):
	""" returns list of all active employees from where date of joining is greater than provided date """
	return frappe.db.get_list("Employee", {'status': 'Active', 'date_of_joining': ('<=', date)}, ["employee"])	

def get_working_employees(date):
	""" returns list of employees who's employee availability status is 'working' for a given date """
	return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Working'})

def get_not_working_employees(date):
	""" returns list of employees who's employee availability status is not working for a given date """
	return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': ('not in', ('Working'))})

@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabEmployee Schedule` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)


@frappe.whitelist()
def get_employees_not_rostered():
	return employees_not_rostered


def get_employee_name(employee_code):
	return frappe.db.get_value("Employee", employee_code, "employee_name")		