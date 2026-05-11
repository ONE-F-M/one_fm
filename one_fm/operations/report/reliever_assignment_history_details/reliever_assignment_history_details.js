// Copyright (c) 2026, One FM and contributors
// For license information, please see license.txt

frappe.query_reports["Reliever Assignment History Details"] = {
	filters: [
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "operations_site",
			label: __("Operations Site"),
			fieldtype: "Link",
			options: "Operations Site",
		},
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
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data) {
			let color = {
				"Completed": "green",
				"Active": "blue",
				"Absent": "red",
				"Planned": "orange",
			}[data.status] || "grey";

			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}

		return value;
	},
};
