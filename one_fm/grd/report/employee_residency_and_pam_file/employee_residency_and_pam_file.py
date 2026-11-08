# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _

FILTER_FIELDS = ("pam_file", "one_fm_nationality")

FIELDS = [
	"name",
	"employee_name",
	"under_company_residency",
	"pam_file",
	"pam_file_number",
	"one_fm_nationality",
	"one_fm_civil_id",
]


def execute(filters=None):
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "under_company_residency",
			"label": _("Under Company Residency"),
			"fieldtype": "Check",
			"width": 150,
		},
		{
			"fieldname": "pam_file",
			"label": _("PAM File"),
			"fieldtype": "Link",
			"options": "PAM License Details",
			"width": 200,
		},
		{
			"fieldname": "pam_file_number",
			"label": _("PAM File Number"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "one_fm_nationality",
			"label": _("Nationality"),
			"fieldtype": "Link",
			"options": "Nationality",
			"width": 150,
		},
		{
			"fieldname": "one_fm_civil_id",
			"label": _("Civil ID"),
			"fieldtype": "Data",
			"width": 150,
		},
	]


def get_data(filters=None):
	filters = filters or {}
	# Filter on the pam_file link only, never on pam_file_number (which can be
	# stored without a link or drift from the linked file). No status filter:
	# all employees are shown, including Left ones.
	query_filters = {k: v for k, v in filters.items() if k in FILTER_FIELDS and v}
	return frappe.get_list(
		"Employee",
		filters=query_filters,
		fields=list(FIELDS),
		order_by="employee_name asc",
	)
