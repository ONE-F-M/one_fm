# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, cint, getdate, add_to_date
from calendar import monthrange
from frappe import msgprint
import pandas as pd


def execute(filters=None):
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
		_("Employees Not Rostered") + ":Int:200",
		_("Employees Not Working") + ":Int:200",
		_("Result") + ":Data:150"
	]	


def get_data(filters=None):
	data = []
	labels = []
	datasets = [
		{"name": "Active Employees\n\n\n", "values": []},
		{"name": "Employees Rostered\n\n\n", "values": []},
		{"name": "Employees Not Rostered\n\n\n", "values": []},
		{"name": "Employees Not Working\n\n\n", "values": []},
	]
	chart = {}
	if filters:
		for date in pd.date_range(start=filters["start_date"], end=filters["end_date"]):
			employee_list = frappe.db.get_list("Employee", {'status': 'Active', 'date_of_joining': ('<=', date)}, ["employee"])			
			rostered_employees_count = len(frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Working'}))
			employee_leave_count = len(frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': ('not in', ('Working'))}))

			employee_not_rostered_count = 0

			for employee in employee_list:
				if not frappe.db.exists({'doctype': 'Employee Schedule', 'date': date, 'employee': employee.employee}):
					employee_not_rostered_count = employee_not_rostered_count + 1

			result = "OK"
			if employee_not_rostered_count > 0:
				result = "NOT OK"

			row = [
				cstr(date).split(" ")[0],
				len(employee_list),
				rostered_employees_count,
				employee_not_rostered_count,
				employee_leave_count,
				result
			]

			data.append(row)

			labels.append("...")
			datasets[0]["values"].append(len(employee_list))
			datasets[1]["values"].append(rostered_employees_count)
			datasets[2]["values"].append(employee_not_rostered_count)
			datasets[3]["values"].append(employee_leave_count)

		chart = {
			"data": {
				"labels": labels,
				"datasets": datasets
			}
		}

		chart["type"] = "line"

	return data, chart

@frappe.whitelist()
def get_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(date) from `tabEmployee Schedule` ORDER BY YEAR(date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)