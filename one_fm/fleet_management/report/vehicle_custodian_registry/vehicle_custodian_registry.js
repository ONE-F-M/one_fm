// Copyright (c) 2026, One FM and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Custodian Registry"] = {
	filters: [
		{
			fieldname: "vehicle",
			label: __("Vehicle Registration"),
			fieldtype: "Link",
			options: "Vehicle",
		},
		{
			fieldname: "vehicle_category",
			label: __("Vehicle Category"),
			fieldtype: "Select",
			options: ["", "Owned", "Leased", "Subcontractor"],
		},
		{
			fieldname: "leasing_company",
			label: __("Leasing Company"),
			fieldtype: "Data",
		},
		{
			fieldname: "employee",
			label: __("Employee ID / Name"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "from_handover_date",
			label: __("From Handover Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_handover_date",
			label: __("To Handover Date"),
			fieldtype: "Date",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Bold the entire row for the current/active custodian.
		if (data && data.is_active_custodian) {
			value = `<span class="font-weight-bold">${value}</span>`;
		}

		return value;
	},
};
