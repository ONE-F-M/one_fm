// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Roster Employee"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"reqd": 1 ,
			"options": [
				{ "value": 1, "label": __("Jan") },
				{ "value": 2, "label": __("Feb") },
				{ "value": 3, "label": __("Mar") },
				{ "value": 4, "label": __("Apr") },
				{ "value": 5, "label": __("May") },
				{ "value": 6, "label": __("June") },
				{ "value": 7, "label": __("July") },
				{ "value": 8, "label": __("Aug") },
				{ "value": 9, "label": __("Sep") },
				{ "value": 10, "label": __("Oct") },
				{ "value": 11, "label": __("Nov") },
				{ "value": 12, "label": __("Dec") },
			],
			"default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Select",
			"reqd": 1
		},
	],
	"onload": function(report) {
		report.page.add_inner_button(__("View employees not rostered"), function() {
			frappe.call({
				method: "one_fm.one_fm.report.roster_employee.roster_employee.get_employees_not_rostered", 
				callback: function(r){
					var employees = r.message;
					message = "<div><b>Employees not rostered: </b><br><ul>";
					for(let i=0;i<employees.length;i++){
						message += "<li>"+ employees[i] + "</li>"
					}
					message += "</ul></div>";
					frappe.msgprint(message)
				}
			})
		}).addClass("btn-primary");
		return  frappe.call({
			method: "one_fm.one_fm.report.roster_employee.roster_employee.get_years",
			callback: function(r) {
				var year_filter = frappe.query_report.get_filter('year');
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n").find(year => year == new Date().getFullYear());
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			}
		});
	}
};
