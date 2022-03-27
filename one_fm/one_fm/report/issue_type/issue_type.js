// Copyright (c) 2016, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

function set_user_department(){
	frappe.db.get_value("Employee", {'user_id': frappe.user.name}, ["department"])
		.then(res => {
			let {department} = res.message;
			frappe.query_reports["Issue Type"].filters[0].default = department;
		})
}

frappe.query_reports["Issue Type"] = {
	"filters": [
		{
			"fieldname":"department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"reqd": 0,
			"default": ""
		},
		{
			"fieldname":"issue_type",
			"label": __("Issue Type"),
			"fieldtype": "Link",
			"options": "Issue Type",
			"reqd": 1,
			"default": 'Other',
			get_query: function() {
				return {
					query: "one_fm.utils.get_issue_type_in_department",
					filters: {"department": frappe.query_report.get_filter_value('department')}
				};
			}
		},
	]
};

set_user_department()