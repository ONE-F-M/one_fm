// Copyright (c) 2024, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Leave Balance Summary"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"mandatory": 1,
			"default": frappe.defaults.get_user_default("Company")
		}
	]
};
