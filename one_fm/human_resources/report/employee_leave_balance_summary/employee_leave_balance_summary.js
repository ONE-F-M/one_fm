// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Leave Balance Summary"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("company")
		}
	]
};
