import frappe

PMR = "Project Manpower Request"
ACTION_TYPE = "Internal Transfer"


def execute():
	"""Set the Internal Transfer fulfillment quantity on PR01180 to 0."""
	rows = frappe.get_all(
		"PMR Fulfillment Action",
		filters={"parent": "PR01180", "parenttype": PMR, "action_type": ACTION_TYPE, "qty": ["!=", 0]},
		pluck="name",
	)
	for row in rows:
		frappe.db.set_value("PMR Fulfillment Action", row, "qty", 0, update_modified=False)
