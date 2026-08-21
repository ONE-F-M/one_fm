# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The monthly penalty report (WI-002015).

Replaces a spreadsheet that was maintained by hand: 11,303 rows in which the same penalty
was written as "Deduct 1 day", "Deduct 1 Day" and "Deduct  2 days" depending on who typed
it. The columns and their order come from that spreadsheet, because it is the report the
department leads already read; what changes is that the values are now derived from the
Penalty And Investigation record rather than retyped.

The same query backs the monthly departmental email (WI-002016), so the two cannot drift
into disagreeing about what a month's penalties were.
"""

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import flt

# AC 1: a penalty is only reportable once it has reached payroll. Anything earlier is still
# being argued about internally and is not a disciplinary fact yet.
REPORTABLE_STATES = ("Pending Payroll Officer", "Completed")

DEDUCTION = "Salary Deduction"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = get_penalties(filters)
	return get_columns(), rows


def get_columns():
	"""The spreadsheet's columns, in the spreadsheet's order.

	"Receipient" is the reporter's spelling and is kept: this is the report the departments
	already know, and quietly renaming its columns is how a reader stops trusting that it is
	the same report.

	The spreadsheet's "Penalty Import Date" is not here. It recorded when a row was pasted
	into the sheet, which is an artefact of maintaining a spreadsheet and has no counterpart
	on a record that knows its own creation date.
	"""
	return [
		{"label": _("Sl.No"), "fieldname": "sl_no", "fieldtype": "Int", "width": 60},
		{"label": _("Violation Date"), "fieldname": "violation_date", "fieldtype": "Date", "width": 110},
		{"label": _("ERP ID"), "fieldname": "issuer", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Issued by"), "fieldname": "issuer_name", "fieldtype": "Data", "width": 180},
		{"label": _("Receiving Date"), "fieldname": "receiving_date", "fieldtype": "Date", "width": 110},
		{"label": _("Serial No."), "fieldname": "penalty_serial_no", "fieldtype": "Data", "width": 100},
		{"label": _("Employee ID (Penalty Receipient)"), "fieldname": "employee_id_number", "fieldtype": "Data", "width": 180},
		{"label": _("ERP ID (Penalty Receipient)"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{"label": _("Location"), "fieldname": "operations_site", "fieldtype": "Link", "options": "Operations Site", "width": 150},
		{"label": _("Type of Violation"), "fieldname": "applied_penalty_code", "fieldtype": "Link", "options": "Penalty Code", "width": 140},
		{"label": _("Violation Category"), "fieldname": "penalty_name", "fieldtype": "Data", "width": 220},
		{"label": _("Penalty"), "fieldname": "penalty", "fieldtype": "Data", "width": 150},
		{"label": _("Status (Employee Response)"), "fieldname": "employee_response", "fieldtype": "Data", "width": 160},
		{"label": _("deductions"), "fieldname": "deductions", "fieldtype": "Currency", "width": 110},
	]


def get_penalties(filters):
	"""The reportable penalties matching the filters, in the report's own column shape.

	Issuer and recipient are both joined to Employee rather than read off the penalty:
	"Issued by" and "Employee ID" have no fields of their own on Penalty And Investigation -
	the record links the two people, and their name and ID belong to them.
	"""
	penalty = DocType("Penalty And Investigation")
	recipient = DocType("Employee").as_("recipient")
	issuer = DocType("Employee").as_("issuer_employee")

	query = (
		frappe.qb.from_(penalty)
		.left_join(recipient).on(penalty.employee == recipient.name)
		.left_join(issuer).on(penalty.issuer == issuer.name)
		.select(
			penalty.name,
			penalty.incident_date.as_("violation_date"),
			penalty.issuer,
			issuer.employee_name.as_("issuer_name"),
			penalty.issuance_date.as_("receiving_date"),
			penalty.penalty_serial_no,
			recipient.employee_id.as_("employee_id_number"),
			penalty.employee,
			penalty.employee_name,
			penalty.operations_site,
			penalty.applied_penalty_code,
			penalty.penalty_name,
			penalty.action_type,
			penalty.salary_deduction_days,
			penalty.employee_response,
			penalty.salary_deduction_amount.as_("deductions"),
		)
		.where(penalty.docstatus < 2)
		.where(penalty.workflow_state.isin(REPORTABLE_STATES))
		.orderby(penalty.incident_date)
		.orderby(penalty.name)
	)

	query = apply_filters(query, penalty, filters)
	rows = query.run(as_dict=True)

	for index, row in enumerate(rows, start=1):
		row.sl_no = index
		row.penalty = format_penalty(row.action_type, row.salary_deduction_days)

	return rows


def apply_filters(query, penalty, filters):
	"""The six filters the story asks for.

	The date range is read against the Violation Date. That is the column the report leads
	with and the date a department recognises a penalty by - the day the incident happened,
	not the day the paperwork caught up with it.
	"""
	if filters.get("from_date"):
		query = query.where(penalty.incident_date >= filters.from_date)
	if filters.get("to_date"):
		query = query.where(penalty.incident_date <= filters.to_date)
	if filters.get("employee"):
		query = query.where(penalty.employee == filters.employee)
	if filters.get("issuer"):
		query = query.where(penalty.issuer == filters.issuer)
	if filters.get("employee_response"):
		query = query.where(penalty.employee_response == filters.employee_response)
	if filters.get("applied_penalty_code"):
		query = query.where(penalty.applied_penalty_code == filters.applied_penalty_code)

	return query


def format_penalty(action_type, salary_deduction_days):
	"""What the Penalty column reads, from the action and the days it deducts.

	The story says these two are "concatenated" and gives "Deduct 1 Day" as the example,
	which is not what concatenating "Salary Deduction" and "1" produces. The spreadsheet
	settles it: a deduction has always been written "Deduct 1 day", and every other action
	has always been written as itself. Confirmed with the reporter.

	Days are printed as typed rather than padded - the spreadsheet has "Deduct 0.5 day"
	alongside "Deduct 4 days", and 0.5 is a real half-day deduction, not a rounding error.
	"""
	if action_type != DEDUCTION:
		return action_type or ""

	days = flt(salary_deduction_days)
	if not days:
		return action_type

	# 1.0 -> "1" but 0.5 stays "0.5", so a whole day does not read "Deduct 1.0 day".
	printed = f"{days:g}"
	return _("Deduct {0} {1}").format(printed, _("day") if days <= 1 else _("days"))
