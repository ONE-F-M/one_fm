# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from warnings import filters
import frappe
from frappe import _
from erpnext.hr.doctype.department.department import get_children

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [
		_("Department") + ":Link/Department:250",
		_("Issue Type") + ":Data:250"
	]
	if filters.get("issue_type") == "Other" or not filters.get("issue_type"):
		columns.append(_("Custom Issue Type") + ":Data:250")
	columns.append(_("Count") + ":Int:250")
	return columns

def get_conditions(filters=None):
	condition = ""
	if filters:
		if filters.get("issue_type"):
			condition += "and issue_type = %(issue_type)s"
		if filters.get("department"):
			condition += "and department in %(department)s"
	return condition

def get_department_children(department, department_list=[]):
	if frappe.db.get_value('Department', department, 'is_group'):
		departments = get_children('Department', parent=department)
		for department in departments:
			is_group = frappe.db.get_value('Department', department.value, 'is_group')
			if is_group:
				get_department_children(department.value, department_list)
			else:
				department_list.append(department.value)
	else:
		department_list.append(department)
	return department_list

def get_data(filters=None):
	condition = get_conditions(filters)
	result = []
	department = []
	if filters.get("department"):
		department = get_department_children(filters.get("department"), [])

	query_res = frappe.db.sql("""
		SELECT
			department, issue_type, your_issue_type, count(*)
		FROM
			`tabIssue`
		WHERE
			docstatus<2 {condition}
		GROUP BY
			department, issue_type, your_issue_type
		HAVING count(*) > 0
	""".format(condition=condition), {'issue_type': filters.get("issue_type"), 'department': department}, as_dict=1)

	for record in query_res:
		row = [
			record["department"],
			record["issue_type"]
		]
		if filters.get("issue_type") == "Other" or not filters.get("issue_type"):
			row.append(record["your_issue_type"])
		row.append(record["count(*)"])
		result.append(row)

	return result
