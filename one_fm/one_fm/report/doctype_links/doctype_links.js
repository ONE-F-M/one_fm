// Copyright (c) 2022, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Doctype Links"] = {
	"filters": [
        {
            "fieldname": "doctype",
            "label": __("DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "reqd": 1,
        },
        {
            "fieldname": "show_permissions",
            "label": __("Show Permissions"),
            "fieldtype": "Check",
            "reqd": 0,
        },

	]
};
