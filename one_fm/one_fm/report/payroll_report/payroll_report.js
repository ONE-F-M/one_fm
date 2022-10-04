// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Payroll Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"reqd": 1 ,
			"options": [
				{ "value": 01, "label": __("Jan") },
				{ "value": 02, "label": __("Feb") },
				{ "value": 03, "label": __("Mar") },
				{ "value": 04, "label": __("Apr") },
				{ "value": 05, "label": __("May") },
				{ "value": 06, "label": __("June") },
				{ "value": 07, "label": __("July") },
				{ "value": 08, "label": __("Aug") },
				{ "value": 09, "label": __("Sep") },
				{ "value": 10, "label": __("Oct") },
				{ "value": 11, "label": __("Nov") },
				{ "value": 12, "label": __("Dec") },
			],
			"default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 01
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Select",
			"reqd": 1
		},
	],
	"onload": function() {
		return  frappe.call({
			method: "one_fm.one_fm.report.payroll_report.payroll_report.get_attendance_years",
			callback: function(r) {
				var year_filter = frappe.query_report.get_filter('year');
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			}
		});	
	},
}
