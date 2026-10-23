// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Colour of the indicator pill per result label. The labels are the ones the Python
// report writes; anything not listed is rendered as plain text.
const ADGA_PILL_COLORS = {
	"Present": "green",
	"Absent": "red",
	"Absent (Uncovered)": "red",
	"Passed": "green",
	"Failed": "red",
	"Not Checked": "gray",
	"Not Started": "gray",
	"Completed": "green",
};

function adga_pill_color(value) {
	if (ADGA_PILL_COLORS[value]) {
		return ADGA_PILL_COLORS[value];
	}
	// "In Progress (Stop N)"
	if (typeof value === "string" && value.indexOf("In Progress") === 0) {
		return "orange";
	}
	return null;
}

frappe.query_reports["Accommodation Dispatch and Grooming Audit"] = {
	tree: true,
	name_field: "row_id",
	parent_field: "parent_trip",
	initial_depth: 0,

	filters: [
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "camp",
			label: __("Camp Facility"),
			fieldtype: "Link",
			options: "Accommodation",
		},
		{
			fieldname: "compliance",
			label: __("Trip Compliance"),
			fieldtype: "Select",
			options: [
				"All Trips",
				"100% Passed Trips",
				"Trips with Absentees",
				"Trips with Grooming/Uniform Fails",
			],
			default: "All Trips",
		},
		{
			fieldname: "search",
			label: __("Search"),
			fieldtype: "Data",
			description: __("Employee Name, Employee ID, Vehicle Plate or Driver Name"),
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		const pill_columns = ["attendance_result", "appearance_result", "lock_status"];
		if (!data || !pill_columns.includes(column.fieldname) || !value) {
			return formatted;
		}
		const color = adga_pill_color(value);
		if (!color) {
			return formatted;
		}
		return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(value)}</span>`;
	},

	onload: function (report) {
		report.page.add_inner_button(__("Export Audit Report"), function () {
			// The export only writes the rows on screen, so open the trips first or
			// the passenger audit trail is missing from the file.
			report.expand_all_rows();
			report.export_report();
		});
	},
};
