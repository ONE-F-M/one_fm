// Copyright (c) 2026, One FM and contributors
// For license information, please see license.txt

frappe.query_reports["Driver Wise Route Timeline"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "driver_name",
			label: __("Driver Name"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "rambo_relief_only",
			label: __("Rambo Relief Only"),
			fieldtype: "Check",
			default: 0,
			on_change: function () {
				frappe.query_report.refresh();
			},
		},
	],

	tree: true,
	name_field: "driver_name",
	parent_field: "",
	initial_depth: 0,

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) {
			return value;
		}

		// Rambo Relief Event — colour-coded indicator pills
		if (column.fieldname === "rambo_relief_event" && data.indent === 0) {
			if (data.rambo_relief_event && data.rambo_relief_event.indexOf("YES") !== -1) {
				value = '<span class="indicator-pill purple">' + __("YES (Standby Deployment)") + "</span>";
			} else if (data.rambo_relief_event && data.rambo_relief_event !== "--") {
				value = '<span class="indicator-pill gray">' + __("NO") + "</span>";
			}
		}

		// Bold driver name on summary rows
		if (column.fieldname === "driver_name" && data.indent === 0) {
			value = "<strong>" + value + "</strong>";
		}

		// Muted styling for detail row placeholders
		if (data.indent === 1) {
			if (column.fieldname === "total_duty_duration" || column.fieldname === "rambo_relief_event") {
				value = '<span class="text-muted">' + value + "</span>";
			}
		}

		return value;
	},
};
