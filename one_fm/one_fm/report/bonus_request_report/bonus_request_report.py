# Copyright (c) 2026, oneaborr and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)

	return columns, data, None, None, report_summary


def get_columns():
	return [
		{
			"fieldname": "employee_id",
			"label": _("Employee ID"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 180,
		},
		{
			"fieldname": "effective_month",
			"label": _("Effective Month"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "effective_year",
			"label": _("Effective Year"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "bonus_amount",
			"label": _("Bonus Amount"),
			"fieldtype": "Currency",
			"width": 150,
		},
	]


def get_data(filters):
	BonusRequest = DocType("Bonus Request")
	BonusRequestItems = DocType("Bonus Request Items")

	query = (
		frappe.qb.from_(BonusRequest)
		.join(BonusRequestItems)
		.on(BonusRequestItems.parent == BonusRequest.name)
		.select(
			BonusRequestItems.employee_id,
			BonusRequestItems.employee_name,
			BonusRequestItems.department,
			BonusRequest.effective_month,
			BonusRequest.effective_year,
			BonusRequestItems.bonus_amount,
		)
		.where(BonusRequest.docstatus == 1)
		.orderby(BonusRequest.effective_year, order=frappe.qb.desc)
		.orderby(BonusRequest.effective_month)
		.orderby(BonusRequestItems.employee_name)
	)

	query = apply_filters(query, filters, BonusRequest, BonusRequestItems)

	data = query.run(as_dict=True)

	for row in data:
		row["effective_year"] = str(row.get("effective_year") or "")

	return data


def apply_filters(query, filters, BonusRequest, BonusRequestItems):
	if filters.get("employee_id"):
		query = query.where(BonusRequestItems.employee_id == filters["employee_id"])

	if filters.get("department"):
		query = query.where(BonusRequestItems.department == filters["department"])

	if filters.get("effective_month"):
		query = query.where(BonusRequest.effective_month == filters["effective_month"])

	if filters.get("effective_year"):
		query = query.where(BonusRequest.effective_year == filters["effective_year"])

	return query


def get_report_summary(data):
	if not data:
		return []

	total_bonus = sum(d.get("bonus_amount") or 0 for d in data)
	total_employees = len(set(d.get("employee_id") for d in data if d.get("employee_id")))

	return [
		{
			"value": total_employees,
			"label": _("Total Employees"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_bonus,
			"label": _("Total Bonus Amount"),
			"datatype": "Currency",
			"indicator": "green",
		},
	]
