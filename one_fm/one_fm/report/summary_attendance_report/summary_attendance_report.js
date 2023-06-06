// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Summary Attendance Report"] = {
	"filters": [
		{
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
			'default':new Date(new Date().getFullYear(), new Date().getMonth(), 1),
            "reqd": 1,
        },
        {
			"fieldname": "to_date",
            "label": __("To Date"),
			"fieldtype": "Date",
            // 'default':new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0),
			'default':frappe.datetime.add_days(frappe.datetime.get_today(), -1),
            "reqd": 1,
        },
	],
};
