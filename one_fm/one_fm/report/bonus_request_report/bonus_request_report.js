// Copyright (c) 2026, oneaborr and contributors
// For license information, please see license.txt

frappe.query_reports["Bonus Request Report"] = {
	filters: [
		{
			fieldname: "employee_id",
			label: __("Employee ID"),
			fieldtype: "Data",
			width: 140,
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "effective_month",
			label: __("Effective Month"),
			fieldtype: "Select",
			options: [
				"",
				"January",
				"February",
				"March",
				"April",
				"May",
				"June",
				"July",
				"August",
				"September",
				"October",
				"November",
				"December",
			],
		},
		{
			fieldname: "effective_year",
			label: __("Effective Year"),
			fieldtype: "Int",
		},
	],
};
