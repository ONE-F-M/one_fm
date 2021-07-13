# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		_("License Name") + ":Link/License:250",
		_("Employee") + ":Link/Employee:250",
		_("Employee Name") + ":Link/Employee:300",
		_("Issue Date") + ":Date:150",
		_("Expiry Date") + ":Date:150"
	]

def get_conditions(filters=None):
	conditions = {}
	if filters:
		if filters.get("license_name"):
			conditions.update({'license_name': filters.get("license_name")})

	return conditions

def get_data(filters=None):
	conditions = get_conditions(filters)
	data = []
	employee_license_list = frappe.db.get_list("Employee License", conditions)
	for employee_license in employee_license_list:
		employee_license_doc = frappe.get_doc("Employee License", employee_license.name)
		row = [
			employee_license_doc.license_name,
			employee_license_doc.employee,
			get_employee_name(employee_license_doc.employee),
			employee_license_doc.issue_date,
			employee_license_doc.expiry_date
		]
		data.append(row)

	return data	

def get_employee_name(employee_code):
	return frappe.db.get_value("Employee", employee_code, "employee_name")		
