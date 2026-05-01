frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Severity Count"] = {
	method: "one_fm.legal.dashboard_chart_source.severity_count.severity_count.get",
	filters: [
		{
			fieldname: "employee_user",
			label: __("Employee User"),
			fieldtype: "Link",
			options: "User",
			default: frappe.session.user,
			read_only: 1
		}
	]
};
