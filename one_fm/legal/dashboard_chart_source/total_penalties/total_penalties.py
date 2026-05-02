import frappe
from frappe import _
from frappe.utils import add_to_date, formatdate, getdate, nowdate
from frappe.utils.dashboard import cache_source
from frappe.utils.dateutils import get_dates_from_timegrain

@frappe.whitelist()
@cache_source
def get(chart_name=None, chart=None,heatmap_year=None, no_cache=None, filters=None, from_date=None, to_date=None, timespan=None, time_interval=None):
	user = frappe.session.user
	
	if chart_name:
		chart = frappe.get_doc("Dashboard Chart", chart_name)
	else:
		chart = frappe._dict(frappe.parse_json(chart))
	
	time_interval = time_interval or chart.time_interval or "Monthly"
	timespan = timespan or chart.timespan or "Last 6 Months"
	
	if timespan == "Select Date Range":
		from_date = from_date or chart.from_date
		to_date = to_date or chart.to_date
	
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_to_date(to_date, months=-60)

	# Define states
	cancelled_states = ["Cancelled by GM", "Cancelled by Supervisor"]
	resolved_states = ["Employee Rejected", "Mark as Completed"]

	# Base filters for current user and not cancelled
	base_filters = [
		["employee_user", "=", user],
		["workflow_state", "not in", cancelled_states]
	]

	# 1. Total count
	total_count = frappe.db.count("Penalty And Investigation", base_filters)

	# 2. Resolved count
	resolved_filters = base_filters + [["workflow_state", "in", resolved_states]]
	resolved_count = frappe.db.count("Penalty And Investigation", resolved_filters)

	# 3. Latest status
	latest_record = frappe.db.get_list("Penalty And Investigation", 
		filters={"employee_user": user}, 
		fields=["workflow_state"], 
		order_by="creation desc", 
		limit=1
	)
	latest_status = latest_record[0].workflow_state if latest_record else _("No Record")

	# 4. Severity counts
	severity_data = frappe.db.get_all("Penalty And Investigation",
		filters={"employee_user": user},
		fields=["applied_level", "count(name) as count"],
		group_by="applied_level"
	)
	
	# Fetch records for timeseries
	records = frappe.db.get_all("Penalty And Investigation",
		filters=base_filters + [["issuance_date", ">=", from_date], ["issuance_date", "<=", to_date]],
		fields=["issuance_date", "workflow_state"],
		order_by="issuance_date asc"
	)

	# Generate dates based on interval
	dates = get_dates_from_timegrain(from_date, to_date, time_interval)
	
	# Prepare datasets
	total_series = []
	resolved_series = []
	
	for date in dates:
		d_total = 0
		d_resolved = 0
		for r in records:
			if getdate(r.issuance_date) <= getdate(date):
				d_total += 1
				if r.workflow_state in resolved_states:
					d_resolved += 1
		total_series.append(d_total)
		resolved_series.append(d_resolved)

	# Summary values
	summary = [
		{"label": _("Total Penalties"), "value": total_count, "indicator": "Red" if total_count > 0 else "Green"},
		{"label": _("Resolved Cases"), "value": resolved_count, "indicator": "Green"},
		{"label": _("Latest Status"), "value": latest_status, "indicator": "Blue"}
	]

	# Add severity levels to summary
	for sd in severity_data:
		level = sd.applied_level or _("N/A")
		summary.append({
			"label": _("Level {0}").format(level),
			"value": sd.count,
			"indicator": "Orange"
		})

	return {
		"labels": [formatdate(d) for d in dates],
		"datasets": [
			{"name": _("Total Penalties"), "values": total_series},
			{"name": _("Resolved Cases"), "values": resolved_series}
		],
		"summary": summary
	}
