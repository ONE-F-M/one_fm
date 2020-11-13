// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.query_reports["Accommodation Meter Reading Report"] = {
	"filters": [
		{
			"fieldname":"accommodation",
			"label": __("Accommodation"),
			"fieldtype": "Link",
			"options": "Accommodation"
		},
		{
			"fieldname":"accommodation_unit",
			"label": __("Accommodation Unit"),
			"fieldtype": "Link",
			"options": "Accommodation Unit"
		},
		{
			"fieldname":"start_date",
			"label": __("From"),
			"fieldtype": "Date",
			"default": moment(frappe.datetime.add_months(frappe.datetime.now_date(), -1)).startOf("month").format()
		},
		{
			"fieldname":"to_date",
			"label": __("To"),
			"fieldtype": "Date",
			"default": moment(frappe.datetime.add_months(frappe.datetime.now_date(), -1)).endOf("month").format()
		}
	]
};
