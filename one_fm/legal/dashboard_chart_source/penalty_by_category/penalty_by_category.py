import frappe
from frappe import _
from frappe.utils import add_to_date, nowdate
from frappe.utils.dashboard import cache_source
from frappe.query_builder import DocType, functions as fn

@frappe.whitelist()
@cache_source
def get(chart_name=None, chart=None, heatmap_year=None, no_cache=None, filters=None, from_date=None, to_date=None, timespan=None, time_interval=None):
	user = frappe.session.user
	
	if chart_name:
		chart = frappe.get_doc("Dashboard Chart", chart_name)
	else:
		chart = frappe._dict(frappe.parse_json(chart)) if chart else frappe._dict()
	
	timespan = timespan or chart.timespan or "Last 6 Months"
	
	if timespan == "Select Date Range":
		from_date = from_date or chart.from_date
		to_date = to_date or chart.to_date
	
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_to_date(to_date, months=-60)

	cancelled_states = ["Cancelled by GM", "Cancelled by Supervisor", "Rejected by Employee"]

	PI = DocType("Penalty And Investigation")
	PC = DocType("Penalty Code")

	query = (
		frappe.qb.from_(PI)
		.join(PC).on(PI.applied_penalty_code == PC.name)
		.select(PC.violation_type, fn.Count(PI.name).as_("count"))
		.where(PI.docstatus != 2)
		.where(PI.workflow_state.notin(cancelled_states))
	)
	
	if from_date:
		query = query.where(PI.issuance_date >= from_date)
	if to_date:
		query = query.where(PI.issuance_date <= to_date)
		
	# Apply dynamic filters
	if filters:
		if isinstance(filters, str):
			filters = frappe.parse_json(filters)
		for key, value in filters.items():
			if value:
				query = query.where(getattr(PI, key) == value)
		
	query = query.groupby(PC.violation_type)
	
	records = query.run(as_dict=True)

	standard_types = ["Work", "Conduct", "Work System"]
	counts_map = {vt: 0 for vt in standard_types}
	
	for r in records:
		vt = r.violation_type or "Unknown"
		if vt not in counts_map:
			counts_map[vt] = 0
		counts_map[vt] += r.count

	labels = list(counts_map.keys())
	values = list(counts_map.values())

	summary = [
		{"label": _("Total Penalties by Category"), "value": sum(values), "indicator": "Blue"}
	]

	return {
		"labels": labels,
		"datasets": [
			{"name": _("Penalties"), "values": values}
		],
		"summary": summary
	}
