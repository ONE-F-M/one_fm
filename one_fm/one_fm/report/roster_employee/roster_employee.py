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
		_("Rostered") + ":Int:200",
		_("Not Rostered") + ":Int:100",
		_("Day Offs") + ":Int:100",
		_("Sick Leaves") + ":Int:100",
		_("Annual Leaves") + ":Int:150",
		_("Emergency Leaves") + ":Int:150",
		_("Result") + ":Data:100"
	]	


def get_data(filters=None):
	data = []
	labels = []
	datasets = [
		{"name": "Active Employees\n\n\n", "values": []},
		{"name": "Rostered\n\n", "values": []},
		{"name": "Not Rostered\n\n", "values": []},
		{"name": "Day Offs\n\n", "values": []},
		{"name": "Sick Leaves\n\n", "values": []},
		{"name": "Annual Leaves\n\n", "values": []},
		{"name": "Emergency Leaves\n\n", "values": []},
	]
	chart = {}
	if filters:
		for date in pd.date_range(start=filters["start_date"], end=filters["end_date"]):
			employee_list = get_active_employees(date)		
			rostered_employees = get_working_employees(date)
			employees_on_day_off = get_day_off_employees(date)
			employees_on_sick_leave = get_sick_leave_employees(date)
			employees_on_annual_leave = get_annual_leave_employees(date)
			employees_on_emergency_leave = get_emergency_leave_employees(date)

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
				len(employees_on_day_off),
				len(employees_on_sick_leave),
				len(employees_on_annual_leave),
				len(employees_on_emergency_leave),
				result			
			]

			data.append(row)

			labels.append("...")
			datasets[0]["values"].append(len(employee_list))
			datasets[1]["values"].append(len(rostered_employees))
			datasets[2]["values"].append(employee_not_rostered_count)
			datasets[3]["values"].append(len(employees_on_day_off))
			datasets[4]["values"].append(len(employees_on_sick_leave))
			datasets[5]["values"].append(len(employees_on_annual_leave))
			datasets[6]["values"].append(len(employees_on_annual_leave))

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

def get_day_off_employees(date):
	""" returns list of employees who's employee availability status is day off for a given date """
	return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Day Off'})

def get_sick_leave_employees(date):
	""" returns list of employees who's employee availability status is sick leave for a given date """
	return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Sick Leave'})

def get_annual_leave_employees(date):
	""" returns list of employees who's employee availability status is annual leave for a given date """
	return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Annual Leave'})

def get_emergency_leave_employees(date):
	""" returns list of employees who's employee availability status is emergency leave for a given date """
	return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Emergency Leave'})

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