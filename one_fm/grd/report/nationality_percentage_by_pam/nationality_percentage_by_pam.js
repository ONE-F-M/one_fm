// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Nationality Percentage by PAM"] = {
	"filters": [
		{
			"fieldname": "pam_file",
			"label": __("PAM File"),
			"fieldtype": "Link",
			"options": "PAM License Details",
			"width": 150,
			"reqd": 0
		}
	]
};
