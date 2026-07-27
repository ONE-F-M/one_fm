// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["User Doctype Permission Insight"] = {
	"filters": [
		{
			"fieldname": "user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User",
			"reqd": 1,
		},
		{
			"fieldname": "target_doctype",
			"label": __("DocType"),
			"fieldtype": "Link",
			"options": "DocType",
			"reqd": 1,
		},
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "status" && data) {
			if (data.user_has_role) {
				value = `<span class="indicator-pill green">${value}</span>`;
			} else {
				value = `<span class="indicator-pill orange">${value}</span>`;
			}
		}
		return value;
	},
};
