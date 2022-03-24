# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from warnings import filters
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		_("Department") + ":Link/Department:250",
		_("Issue Type") + ":Data:250",
		_("Custom Issue Type") + ":Data:250",
		_("Count") + ":Int:250"
	]

def get_conditions(filters=None):
	conditions = {}
	if filters:
		if filters.get("department"):
			conditions.update({'department': filters.get("department")})
		
		if filters.get("issue_type"):
			conditions.update({'issue_type': filters.get("issue_type")})

	return conditions

def get_data(filters=None):
	conditions = get_conditions(filters)
	result = []

	query_res = frappe.db.sql("""
		SELECT department, issue_type, your_issue_type, count(*) from `tabIssue`
		WHERE issue_type = %(issue_type)s AND department = %(department)s
		GROUP BY department, your_issue_type
		HAVING count(*) > 0
	""", {'issue_type': conditions.get("issue_type"), 'department': conditions.get("department")}, as_dict=1)

	for record in query_res:
		row = [
			record["department"],
			record["issue_type"],
			record["your_issue_type"] if record["your_issue_type"] else "",
			record["count(*)"]
		]

		result.append(row)
	
	return result