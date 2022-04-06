// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase Request"] = {
	"filters": [
		{
			"fieldname":"requested_by",
			"label": __("Requested By"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname":"from_date",
			"label": __("From"),
			"fieldtype": "Date"
		},
		{
			"fieldname":"to_date",
			"label": __("To"),
			"fieldtype": "Date"
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname":"docstatus",
			"label":__("Status"),
			"fieldtype":"Select",
			"options":["", "Pending", "Submitted", "Rejected"]
		}
	]
}
