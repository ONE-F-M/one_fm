// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Head Hunt Count"] = {
	"filters": [
		{
			"fieldname":"source",
			"label": __("Source"),
			"fieldtype": "Link",
			"options":"User"
		},
		{
			"fieldname":"from_date",
			"label": __("From"),
			"fieldtype": "Date",
		},
		{
			"fieldname":"to_date",
			"label": __("To"),
			"fieldtype": "Date",
		},
	]
};
