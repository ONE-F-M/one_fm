// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["One FM Penalty Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "employee",
			label: __("Recipient Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "issuer",
			label: __("Issued Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "employee_response",
			label: __("Employee Response"),
			fieldtype: "Select",
			options: [
				"",
				"Accepted",
				"Refused",
				"Not Return from Vacation",
				"Request for Investigation by Employee",
			],
		},
		{
			fieldname: "applied_penalty_code",
			label: __("Penalty Code"),
			fieldtype: "Link",
			options: "Penalty Code",
		},
	],
};
