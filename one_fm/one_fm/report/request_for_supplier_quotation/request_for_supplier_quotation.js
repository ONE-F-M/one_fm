// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Request for Supplier Quotation"] = {
	"filters": [
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
			"fieldname":"docstatus",
			"label":__("Status"),
			"fieldtype":"Select",
			"options":["", "Pending", "Submitted", "Rejected"]
		}
	]
}
