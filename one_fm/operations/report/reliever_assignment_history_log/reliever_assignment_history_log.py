# Copyright (c) 2026, One FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import getdate, add_days, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)

	return columns, data, None, None, report_summary


def get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "reliever_type",
			"label": _("Reliever Type"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 150,
		},
		{
			"fieldname": "operations_role",
			"label": _("Operations Role"),
			"fieldtype": "Link",
			"options": "Operations Role",
			"width": 150,
		},
		{
			"fieldname": "operations_site",
			"label": _("Operations Site"),
			"fieldtype": "Link",
			"options": "Operations Site",
			"width": 150,
		},
		{
			"fieldname": "shift_classification",
			"label": _("Shift Classification"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "replaced_employee",
			"label": _("Replaced Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
		{
			"fieldname": "replaced_employee_name",
			"label": _("Replaced Employee Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "from_date",
			"label": _("From Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "to_date",
			"label": _("To Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "number_of_days_worked",
			"label": _("Number of Days Worked"),
			"fieldtype": "Int",
			"width": 100,
		},
	]


def get_data(filters):
	records = get_raw_records(filters)

	if not records:
		return []

	# Fetch reliever type info for all employees in the result set
	employee_ids = list(set([r.employee for r in records]))
	reliever_type_map = get_reliever_type_map(employee_ids)

	# Fetch replaced employee info
	replaced_schedule_ids = list(set([
		r.replaced_employee_schedule for r in records
		if r.replaced_employee_schedule
	]))
	replaced_employee_map = get_replaced_employee_map(replaced_schedule_ids)

	# Group consecutive records into blocks
	grouped = group_consecutive_records(records, reliever_type_map, replaced_employee_map)

	return grouped


def get_raw_records(filters):
	ES = DocType("Employee Schedule")
	OS = DocType("Operations Shift")

	query = (
		frappe.qb.from_(ES)
		.left_join(OS).on(ES.shift == OS.name)
		.select(
			ES.name.as_("schedule_name"),
			ES.employee,
			ES.employee_name,
			ES.date,
			ES.operations_role,
			ES.shift,
			OS.site.as_("operations_site"),
			OS.project,
			OS.shift_classification,
			ES.replaced_employee_schedule,
		)
		.where(ES.is_relieving_schedule == 1)
		.orderby(ES.employee)
		.orderby(ES.date)
	)

	query = apply_filters(query, filters, ES, OS)

	return query.run(as_dict=True)


def apply_filters(query, filters, ES, OS):
	if not filters:
		return query

	if filters.get("employee"):
		query = query.where(ES.employee == filters["employee"])

	if filters.get("project"):
		query = query.where(OS.project == filters["project"])

	if filters.get("operations_site"):
		query = query.where(OS.site == filters["operations_site"])

	if filters.get("from_date"):
		query = query.where(ES.date >= filters["from_date"])

	if filters.get("to_date"):
		query = query.where(ES.date <= filters["to_date"])

	return query


def get_reliever_type_map(employee_ids):
	"""Fetch reliever type flags for employees."""
	if not employee_ids:
		return {}

	Employee = DocType("Employee")
	employees = (
		frappe.qb.from_(Employee)
		.select(
			Employee.name,
			Employee.custom_is_reliever,
			Employee.custom_is_weekend_reliever,
		)
		.where(Employee.name.isin(employee_ids))
	).run(as_dict=True)

	type_map = {}
	for emp in employees:
		types = []
		if emp.custom_is_reliever:
			types.append(_("Day Off Reliever"))
		if emp.custom_is_weekend_reliever:
			types.append(_("Weekend Reliever"))
		type_map[emp.name] = ", ".join(types) if types else "\u2014"

	return type_map


def get_replaced_employee_map(schedule_ids):
	"""Fetch the employee details from replaced employee schedules."""
	if not schedule_ids:
		return {}

	ES = DocType("Employee Schedule")
	records = (
		frappe.qb.from_(ES)
		.select(ES.name, ES.employee, ES.employee_name)
		.where(ES.name.isin(schedule_ids))
	).run(as_dict=True)

	return {r.name: r for r in records}


def group_consecutive_records(records, reliever_type_map, replaced_employee_map):
	"""
	Group consecutive reliever assignments into blocks.

	A block is broken when any of the following change between consecutive records:
	- employee (the reliever)
	- replaced employee (derived from replaced_employee_schedule)
	- operations_site
	- project
	- operations_role
	- shift
	- date gap (not consecutive)
	"""
	if not records:
		return []

	grouped = []
	current_block = None

	for record in records:
		# Get the replaced employee from the map
		replaced_info = replaced_employee_map.get(record.replaced_employee_schedule, {})
		replaced_employee = replaced_info.get("employee", "") if replaced_info else ""

		# Build the grouping key
		group_key = (
			record.employee,
			replaced_employee,
			record.operations_site,
			record.project,
			record.operations_role,
			record.shift,
		)

		if current_block is None:
			# Start the first block
			current_block = _start_new_block(record, group_key, replaced_info, reliever_type_map)
		else:
			# Check if this record continues the current block
			prev_date = current_block["_last_date"]
			current_date = getdate(record.date)
			is_consecutive = (current_date - prev_date).days == 1
			same_group = current_block["_group_key"] == group_key

			if is_consecutive and same_group:
				# Extend current block
				current_block["to_date"] = record.date
				current_block["number_of_days_worked"] += 1
				current_block["_last_date"] = current_date
			else:
				# Emit current block, start new one
				grouped.append(_finalize_block(current_block))
				current_block = _start_new_block(record, group_key, replaced_info, reliever_type_map)

	# Emit the last block
	if current_block:
		grouped.append(_finalize_block(current_block))

	return grouped


def _start_new_block(record, group_key, replaced_info, reliever_type_map):
	"""Initialize a new grouping block."""
	return {
		"employee": record.employee,
		"employee_name": record.employee_name,
		"reliever_type": reliever_type_map.get(record.employee, "\u2014"),
		"project": record.project,
		"operations_role": record.operations_role,
		"operations_site": record.operations_site,
		"shift_classification": record.shift_classification,
		"replaced_employee": replaced_info.get("employee", "") if replaced_info else "",
		"replaced_employee_name": replaced_info.get("employee_name", "") if replaced_info else "",
		"from_date": record.date,
		"to_date": record.date,
		"number_of_days_worked": 1,
		"_group_key": group_key,
		"_last_date": getdate(record.date),
	}


def _finalize_block(block):
	"""Remove internal tracking keys before returning."""
	block.pop("_group_key", None)
	block.pop("_last_date", None)
	return block


def get_report_summary(data):
	if not data:
		return []

	total_blocks = len(data)
	total_days = sum(d.get("number_of_days_worked", 0) for d in data)
	unique_relievers = len(set(d.get("employee", "") for d in data))

	return [
		{
			"value": total_blocks,
			"label": _("Total Assignment Blocks"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_days,
			"label": _("Total Days Worked"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": unique_relievers,
			"label": _("Unique Relievers"),
			"datatype": "Int",
			"indicator": "blue",
		},
	]
