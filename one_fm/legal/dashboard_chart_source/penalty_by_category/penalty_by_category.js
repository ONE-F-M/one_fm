frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Penalty by Category"] = {
	method: "one_fm.legal.dashboard_chart_source.penalty_by_category.penalty_by_category.get",
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
