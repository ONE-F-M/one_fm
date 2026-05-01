frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Total Penalties"] = {
	method: "one_fm.legal.dashboard_chart_source.total_penalties.total_penalties.get",
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
