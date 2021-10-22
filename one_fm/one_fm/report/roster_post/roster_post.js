// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Roster Post"] = {
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
			"reqd": 1,
			"options": [
				{ "value": 2016, "label": __("2016") },
				{ "value": 2017, "label": __("2017") },
				{ "value": 2018, "label": __("2018") },
				{ "value": 2019, "label": __("2019") },
				{ "value": 2020, "label": __("2020") },
				{ "value": 2021, "label": __("2021") },
				{ "value": 2022, "label": __("2022") },
				{ "value": 2023, "label": __("2023") },
				{ "value": 2024, "label": __("2024") },
				{ "value": 2025, "label": __("2025") },
				{ "value": 2026, "label": __("2026") },
				{ "value": 2027, "label": __("2027") },
				{ "value": 2028, "label": __("2028") },
			],
			"default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).getFullYear()
		},
	],
	"onload": function(report) {
		report.page.add_inner_button(__("View post types not filled"), function() {
			frappe.call({
				method: "one_fm.one_fm.report.roster_post.roster_post.get_post_types_not_filled", 
				callback: function(r){
					var post_types = r.message;
					message = "<div><b>Post types not filled: </b><br><ul>";
					for(let i=0;i<post_types.length;i++){
						message += "<li>"+ post_types[i] + "</li>"
					}
					message += "</ul></div>";
					frappe.msgprint(message)
				}
			})
		}).addClass("btn-primary");
	}
};
