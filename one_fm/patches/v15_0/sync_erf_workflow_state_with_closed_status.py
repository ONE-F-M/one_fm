import frappe


def execute():
	"""Set workflow_state to 'Closed' for ERFs whose status is 'Closed' but
	whose workflow_state is out of sync (anything other than 'Closed')."""
	erf_names = frappe.get_all(
		"ERF",
		filters={"status": "Closed", "workflow_state": ["!=", "Closed"]},
		pluck="name",
	)

	if not erf_names:
		return

	frappe.db.set_value(
		"ERF",
		{"name": ["in", erf_names]},
		"workflow_state",
		"Closed",
		update_modified=False,
	)
