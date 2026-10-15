# Copyright (c) 2026, One FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

ROSTER_TYPE = "Over-Time"
PENDING = "Pending DSOT Approval"
ACTIVE = "Active"
REJECTED = "Rejected"

# What the user picks in the Workflow State filter, and the state it means on the record.
# An approved DSOT is not a state of its own: Approve moves the row to Active.
STATE_FOR_OPTION = {
	"Pending DSOT Approval": PENDING,
	"Approved": ACTIVE,
	"Rejected": REJECTED,
}
OPTION_FOR_STATE = {state: option for option, state in STATE_FOR_OPTION.items()}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)
	label_workflow_states(data)

	return columns, data, None, None, report_summary


def validate_filters(filters):
	if not filters.from_date or not filters.to_date:
		frappe.throw(_("From Date and To Date are required."))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	if filters.workflow_state and filters.workflow_state not in STATE_FOR_OPTION:
		frappe.throw(_("Workflow State must be one of: {0}").format(
			", ".join(STATE_FOR_OPTION)))


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Schedule ID"),
			"fieldtype": "Link",
			"options": "Employee Schedule",
			"width": 220,
		},
		{
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "employee",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 140,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 180,
		},
		{
			"fieldname": "site",
			"label": _("Site"),
			"fieldtype": "Link",
			"options": "Operations Site",
			"width": 150,
		},
		{
			"fieldname": "shift",
			"label": _("Operations Shift"),
			"fieldtype": "Link",
			"options": "Operations Shift",
			"width": 200,
		},
		{
			"fieldname": "operations_role",
			"label": _("Operations Role"),
			"fieldtype": "Link",
			"options": "Operations Role",
			"width": 150,
		},
		{
			"fieldname": "start_datetime",
			"label": _("Start Datetime"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "end_datetime",
			"label": _("End Datetime"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "workflow_state",
			"label": _("Workflow State"),
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data(filters):
	rows = frappe.get_list(
		"Employee Schedule",
		filters=get_filters(filters),
		fields=[
			"name",
			"date",
			"employee",
			"employee_name",
			"project",
			"site",
			"shift",
			"operations_role",
			"start_datetime",
			"end_datetime",
			"workflow_state",
		],
		order_by="date desc, employee asc",
		limit_page_length=0,
	)

	# The summary is counted from these rows by the caller, so keep the stored state on
	# each row and only relabel it once the counts have been taken.
	return rows


def get_filters(filters):
	# dsot_request is the only thing that marks a row as a DSOT. Over-Time rows without
	# it are ordinary overtime, and an Active row alone does not say it was ever held.
	conditions = {
		"roster_type": ROSTER_TYPE,
		"dsot_request": ["is", "set"],
		"date": ["between", [getdate(filters.from_date), getdate(filters.to_date)]],
	}

	if filters.workflow_state:
		conditions["workflow_state"] = STATE_FOR_OPTION[filters.workflow_state]
	else:
		conditions["workflow_state"] = ["in", [PENDING, ACTIVE, REJECTED]]

	if filters.project:
		conditions["project"] = filters.project
	if filters.site:
		conditions["site"] = filters.site
	if filters.employee:
		conditions["employee"] = filters.employee

	return conditions


def get_report_summary(data):
	counts = {PENDING: 0, ACTIVE: 0, REJECTED: 0}
	for row in data:
		if row.workflow_state in counts:
			counts[row.workflow_state] += 1

	return [
		{
			"value": counts[PENDING],
			"label": _("Pending DSOT Approval"),
			"datatype": "Int",
			"indicator": "Orange",
		},
		{
			"value": counts[ACTIVE],
			"label": _("Approved DSOT"),
			"datatype": "Int",
			"indicator": "Green",
		},
		{
			"value": counts[REJECTED],
			"label": _("Rejected DSOT"),
			"datatype": "Int",
			"indicator": "Red",
		},
	]
