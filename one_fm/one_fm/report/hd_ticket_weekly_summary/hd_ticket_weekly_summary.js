// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.query_reports["HD Ticket Weekly Summary"] = {
	"filters": [
		{
			"fieldname": "start_date",
			"fieldtype": "Date",
			"label": "Start Date",
			"reqd": 1,
			"default": frappe.datetime.add_days(frappe.datetime.now_date(), -6)
		},
		{
			"fieldname": "end_date",
			"fieldtype": "Date",
			"label": "End Date",
			"reqd": 1,
			"default": frappe.datetime.now_date()
		},
	]
};
