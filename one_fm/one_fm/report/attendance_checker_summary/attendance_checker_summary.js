// Copyright (c) 2023, omar jaber and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Attendance Checker Summary"] = {
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
			'default':new Date(new Date().getFullYear(), new Date().getMonth(), -1),
            "reqd": 1,
        },
	],
	"initial_depth": 3,
	"tree": true,
	"parent_field": "parent",
	"name_field": "attendance_value"
};
