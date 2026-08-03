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
			on_change: apply_in_page_filters,
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "employee_status",
			on_change: apply_in_page_filters,
			label: __("Employee Status"),
			fieldtype: "Select",
			// Blank means every status, so a payroll run can include leavers.
			options: ["", "Active", "Inactive", "Suspended", "Left"],
		},
		{
			fieldname: "employment_type",
			on_change: apply_in_page_filters,
			label: __("Employment Type"),
			fieldtype: "Link",
			options: "Employment Type",
		},
		{
			fieldname: "roster_type",
			on_change: apply_in_page_filters,
			label: __("Roster Type"),
			fieldtype: "Select",
			options: ["", "Basic", "Over-Time"],
		},
		{
			fieldname: "day_off_ot",
			on_change: apply_in_page_filters,
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
	onload: function () {
		attach_status_map();
	},
	after_datatable_render: function () {
		remember_server_rows();
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


// --- In-page filters -------------------------------------------------------------
// Only the dates, Include Future Attendance and Generate Based On change what the
// server has to fetch. The rest just narrow the rows already on screen, so they run
// here: Frappe calls a filter's on_change in place of refreshing the report, which is
// what stops every tick of a checkbox queuing another background run.

// Project is deliberately absent: it also narrows the Attendance rows themselves
// (Attendance.project), so an employee with days booked to another project would come
// out differently in page than the server returns.
const IN_PAGE_FILTERS = [
	"employee",
	"employee_status",
	"employment_type",
	"roster_type",
	"day_off_ot",
];

let server_rows = null;
let filtering_in_page = false;

function remember_server_rows() {
	// Keep the unfiltered set the server last sent, so narrowing is always applied to
	// the whole thing rather than to what a previous filter left behind.
	if (filtering_in_page) return;
	const report = frappe.query_report;
	if (report && report.data) server_rows = report.data.slice();
}

function row_matches(row, filters) {
	if (filters.employee && row.employee !== filters.employee) return false;
	if (filters.employee_status && row.employee_status !== filters.employee_status) return false;
	if (filters.employment_type && row.employment_type !== filters.employment_type) return false;
	// The same rules the query applies, so the two agree whichever path ran:
	//   Basic, unchecked    -> basic only, day-off OT actively excluded
	//   Basic, checked      -> only basic rows flagged day-off OT
	//   Overtime, unchecked -> overtime only
	//   Overtime, checked   -> nothing (Logic Rule 4)
	if (filters.roster_type && row.roster_type !== filters.roster_type) return false;
	if (filters.day_off_ot) {
		if (cint(row.day_off_ot) !== 1) return false;
	} else if (filters.roster_type === "Basic" && cint(row.day_off_ot) === 1) {
		return false;
	}

	return true;
}

function cint(value) {
	return parseInt(value, 10) || 0;
}

function apply_in_page_filters() {
	const report = frappe.query_report;
	if (!report || !report.datatable) return;
	if (!server_rows) server_rows = (report.data || []).slice();

	const filters = {};
	IN_PAGE_FILTERS.forEach((fieldname) => {
		filters[fieldname] = report.get_filter_value(fieldname);
	});

	const rows = server_rows.filter((row) => row_matches(row, filters));

	filtering_in_page = true;
	try {
		report.datatable.refresh(rows);
	} finally {
		filtering_in_page = false;
	}
}
