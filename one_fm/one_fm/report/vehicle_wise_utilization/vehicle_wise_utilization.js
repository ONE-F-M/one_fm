// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Wise Utilization"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "vehicle_no",
			label: __("Vehicle No"),
			fieldtype: "Link",
			options: "Vehicle",
		},
		{
			fieldname: "operations_site",
			label: __("Operations Site"),
			fieldtype: "Link",
			options: "Operations Site",
		},
	],
};
