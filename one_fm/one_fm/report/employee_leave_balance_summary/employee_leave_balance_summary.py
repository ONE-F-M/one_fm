# Copyright (c) 2024, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"label": _("Employee ID"),
			"fieldname": "employee_id",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Available Sick Leave Days"),
			"fieldname": "available_sick_leave_days",
			"fieldtype": "float",
			"width": 200
		}
	]

def get_data(filters):
	data = []
	company = filters.get("company")
	
	employees = frappe.get_all("Employee", 
		filters={"company": company, "status": "Active"}, 
		fields=["name", "employee_name"]
	)
	
	leave_type = "Sick Leave"
	date = frappe.utils.today()
	
	for employee in employees:
		leave_balance = get_leave_balance_on(employee.name, leave_type, date)
		data.append({
			"employee_id": employee.name,
			"employee_name": employee.employee_name,
			"available_sick_leave_days": leave_balance
		})
	
	return data
