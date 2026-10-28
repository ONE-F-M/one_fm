// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Residency and PAM File"] = {
	"filters": [
		{
			"fieldname": "pam_file",
			"label": __("PAM File"),
			"fieldtype": "Link",
			"options": "PAM License Details"
		},
		{
			"fieldname": "one_fm_nationality",
			"label": __("Nationality"),
			"fieldtype": "Link",
			"options": "Nationality"
		}
	]
};
