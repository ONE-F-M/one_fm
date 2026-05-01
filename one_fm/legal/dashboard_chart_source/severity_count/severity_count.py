import frappe
from frappe import _
from frappe.query_builder import DocType, functions as fn

@frappe.whitelist()
def get(chart_name=None, chart=None, no_cache=None, filters=None):
	user = frappe.session.user
	
	PI = DocType("Penalty And Investigation")
	PC = DocType("Penalty Code")
	
	# Fetch counts grouped by severity level
	query = (
		frappe.qb.from_(PI)
		.join(PC).on(PI.applied_penalty_code == PC.name)
		.select(PC.severity_level, fn.Count(PI.name).as_("count"))
		.where(PI.employee_user == user)
		.where(PI.docstatus != 2)
		.groupby(PC.severity_level)
	)
	
	data = query.run(as_dict=True)
	
	labels = []
	values = []
	summary = []
	
	# Define a fixed order for severity levels
	severity_order = ["Minor", "Major", "Critical"]
	data_map = {d.severity_level: d.count for d in data}
	
	for severity in severity_order:
		count = data_map.get(severity, 0)
		labels.append(_(severity))
		values.append(count)
		summary.append({
			"label": _(severity),
			"value": count,
			"indicator": "Green" if severity == "Minor" else "Orange" if severity == "Major" else "Red"
		})
	
	# Handle any other severity levels not in the order list
	for d in data:
		if d.severity_level not in severity_order:
			labels.append(d.severity_level or _("N/A"))
			values.append(d.count)
			summary.append({
				"label": d.severity_level or _("N/A"),
				"value": d.count,
				"indicator": "Grey"
			})

	return {
		"labels": labels,
		"datasets": [
			{
				"name": _("Severity Count"),
				"values": values
			}
		],
		"summary": summary
	}
