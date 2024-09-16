// Copyright (c) 2024, omar jaber and contributors
// For license information, please see license.txt

frappe.query_reports["Duplicate Attendance"] = {
	"filters": [
		{
			"fieldname":"attendance_date",
			"label": __("Attendance Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.now_date()
		},
		{
			"fieldname":"roster_type",
			"label": __("Roster Type"),
			"fieldtype": "Select",
			"options": ["Basic", "Over-Time"],
			"reqd": 1,
			"default": "Basic"
		},
		{
			"fieldname":"status",
			"label": __("Status"),
			"fieldtype": "Select",
            "options": ["", "Present", "Absent", "On Leave", "Half Day", "Work From Home"]
		},
	]
};
