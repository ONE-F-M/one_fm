// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employees Not Using App"] = {
	"filters": [
		{
            "fieldname": "date",
            "label": __("Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.get_today()
        },
		{
            "fieldname": "supervisor",
            "label": __("Supervisor"),
            "fieldtype": "Link",
            "reqd": 0,
			"read_only": frappe.user.has_role('HR Manager') ? 0 : 1,
            "options": "Employee",
			"default": frappe.db.get_value('Employee', {'user_id':frappe.session.user}, 'name').then(
				res=>{
					frappe.query_report.set_filter_value('supervisor', res.message.name);
				}
			)
        },
		{
            "fieldname": "company",
            "label": __("Company"),
			"options": "Company",
            "fieldtype": "Link",
            "reqd": 1,
            "default": frappe.defaults.get_default('company')

        }
	]
};


