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
            "options": "Employee"
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


