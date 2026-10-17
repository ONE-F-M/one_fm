// Copyright (c) 2026, One FM and contributors
// For license information, please see license.txt

frappe.query_reports["DSOT Employee Schedule"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
		},
		{
			fieldname: "site",
			label: __("Site"),
			fieldtype: "Link",
			options: "Operations Site",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "workflow_state",
			label: __("Workflow State"),
			fieldtype: "Select",
			options: "\nPending DSOT Approval\nApproved\nRejected",
		},
	],
};
