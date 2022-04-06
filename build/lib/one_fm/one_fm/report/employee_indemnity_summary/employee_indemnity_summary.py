# Copyright (c) 2022, omar jaber, Anthony Emmanuel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_data(filters):
	condition = "";
	if filters.department:
		condition += f' AND department="{filters.department}"'
	if filters.employee:
		condition += f' AND employee="{filters.employee}"'

	query = frappe.db.sql(f"""
		SELECT employee, employee_name, department, exit_status,
		indemnity_amount, transaction_date, indemnity_allocation, indemnity_policy
		FROM `tabEmployee Indemnity`
		WHERE transaction_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'
		{condition}
		ORDER BY transaction_date ASC
	;""", as_dict=1)

	return query

def get_columns():
	return [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
		{"label": _("Amount"), "fieldname": "indemnity_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "width": 150, "options": "Department"},
		{"label": _("Exist Status"), "fieldname": "exit_status", "fieldtype": "Data", "width": 120},
		{"label": _("Indemnity Allocation"), "fieldname": "indemnity_allocation", "fieldtype": "Link", "width": 150, "options": "Indemnity Allocation"},
		{"label": _("Indemnity Policy"), "fieldname": "indemnity_policy", "fieldtype": "Link", "width": 180, "options": "Indemnity Policy"},
	]
