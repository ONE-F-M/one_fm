// Copyright (c) 2025, ONE FM and contributors
// For license information, please see license.txt

const status_color_map = {
	"P": "green",
	"A": "red",
	"OL": "red",
	"H": "blue",
	"DO": "blue",
	"CDO": "blue"
};

// Fixed columns before the per-day cells; the formatter colours only the day cells.
const FIXED_COLUMNS = 8;

frappe.query_reports["Operations Monthly Attendance Sheet"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "employee_status",
			label: __("Employee Status"),
			fieldtype: "Select",
			// Blank means every status, so a payroll run can include leavers.
			options: ["", "Active", "Inactive", "Suspended", "Left"],
		},
		{
			fieldname: "employment_type",
			label: __("Employment Type"),
			fieldtype: "Link",
			options: "Employment Type",
		},
		{
			fieldname: "roster_type",
			label: __("Roster Type"),
			fieldtype: "Select",
			options: ["", "Basic", "Over-Time"],
		},
		{
			fieldname: "day_off_ot",
			label: __("Day Off OT"),
			fieldtype: "Check",
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
			depends_on: "eval: doc.project",
			get_query: function () {
				const project = frappe.query_report.get_filter_value("project");
				return {
					filters: {
						project: project || ""
					}
				};
			}
		},
		{
			fieldname: "generate_based_on",
			label: __("Generate Based On"),
			fieldtype: "Select",
			options: ["Attendance Status", "Shift Hours"],
			default: "Attendance Status",
		},
		{
			fieldname: "include_future_attendance",
			label: __("Include Future Attendance"),
			fieldtype: "Check",
		},
		{
			// Gates the run. The report opens empty and is built only when Generate is
			// clicked, because a payroll extract over every employee is far too
			// expensive to re-run on each filter change. Hidden: it is driven by the
			// button, not set by hand.
			fieldname: "generate",
			label: __("Generate"),
			fieldtype: "Check",
			hidden: 1,
			default: 0,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.colIndex < FIXED_COLUMNS) return value;
		// Under "Shift Hours" the day cells hold a duration, which has no status colour
		// (WI-001791) - colour only what the map knows.
		const color = status_color_map[value];
		if (!color) return value;
		return `<span style='color:${color}'>${value}</span>`;
	},
	onload: function (report) {
		report.page.add_inner_button(__("Generate"), () => {
			// Every filter change clears the flag again (see get_filter below), so the
			// figures on screen always belong to the filters that produced them.
			report.set_filter_value("generate", 1);
		});

		// Any filter change invalidates what is on screen: blank the report rather
		// than leave stale numbers under new filter values.
		report.filters
			.filter((f) => f.df.fieldname !== "generate")
			.forEach((filter) => {
				const original = filter.df.onchange;
				filter.df.onchange = function () {
					if (original) original.apply(this, arguments);
					if (frappe.query_report.get_filter_value("generate")) {
						frappe.query_report.set_filter_value("generate", 0);
					}
				};
			});

		attach_status_map();
	},
	after_datatable_render: function () {
		// The print template needs the day headers for the range actually rendered.
		attach_report_additional_day_details();
	}
};

function attach_report_additional_day_details () {
	const report = frappe.query_report;

	const from_date = report.get_filter_value("from_date");
	const to_date = report.get_filter_value("to_date");
	if (!from_date || !to_date) return;

	return frappe.call({
		method: "one_fm.one_fm.report.operations_monthly_attendance_sheet.operations_monthly_attendance_sheet.get_report_additional_day_details",
		args: { from_date: from_date, to_date: to_date },
		callback: function (res) {
			frappe.query_report.additional_details = {
				...(report.additional_details || {}),
				days: res.message
			};
		},
	});
}

function attach_status_map () {
	const report = frappe.query_report;

	return frappe.call({
		method: "one_fm.one_fm.report.operations_monthly_attendance_sheet.operations_monthly_attendance_sheet.get_attendance_status_map",
		callback: function (res) {
			frappe.query_report.additional_details = {
				...(report.additional_details || {}),
				status_map: Object.entries(res.message).map(([status, key]) => ({ status, key }))
			};
		},
	});
}
