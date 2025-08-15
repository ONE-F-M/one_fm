// Copyright (c) 2025, omar jaber and contributors
// For license information, please see license.txt

const status_color_map = {
	"P": "green",
	"A": "red",
	"OL": "red",
	"H": "blue",
	"DO": "blue",
	"CDO": "blue"
};

frappe.query_reports["Operations Monthly Attendance Sheet"] = {
	"filters": [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			reqd: 1,
			options: [
				{ value: 1, label: __("January") },
				{ value: 2, label: __("February") },
				{ value: 3, label: __("March") },
				{ value: 4, label: __("April") },
				{ value: 5, label: __("May") },
				{ value: 6, label: __("June") },
				{ value: 7, label: __("July") },
				{ value: 8, label: __("August") },
				{ value: 9, label: __("September") },
				{ value: 10, label: __("October") },
				{ value: 11, label: __("November") },
				{ value: 12, label: __("December") },
			],
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
			on_change: function (report) {
				attach_report_additional_day_details().then(() => {
					report.refresh();
				})
			}
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			reqd: 1,
			on_change: function (report) {
				attach_report_additional_day_details().then(() => {
					report.refresh();
				})
			}
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			reqd: 1,
			on_change: function (report) {
				report.refresh();
				const project = report.get_filter("project").get_value();
				if (project) {
					frappe.call({
						method: "frappe.client.get",
						args: {
							doctype: "Project",
							name: project
						},
						callback: function(r) {
							frappe.query_report.additional_details = {
								...(report.additional_details || {}),
								client_logo: r.message.project_image || ""
							};
						}
					});
				}
			}
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
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return column.colIndex < 3 ? value : `<span style='color:${status_color_map[value]}'>${value}</span>`;
	},
	onload: function (report) {
		return frappe.call({
			method: "one_fm.one_fm.report.operations_monthly_attendance_sheet.operations_monthly_attendance_sheet.get_attendance_years",
			callback: function (r) {
				const year_filter = report.get_filter("year")
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
				attach_report_additional_day_details()
				attach_status_map()
			},
		});
	}
};

function attach_report_additional_day_details () {
	const report = frappe.query_report;

	const selectedMonth = report.get_filter("month").value
	const selectedYear = report.get_filter("year").value

	return frappe.call({
		method: "one_fm.one_fm.report.operations_monthly_attendance_sheet.operations_monthly_attendance_sheet.get_report_additional_day_details",
		args: {
			month: selectedMonth,
			year: selectedYear
		},
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
