import frappe


def execute():
	"""Move Arrival and Deployment's workflow_state Custom Field to permlevel 1.

	Pairs with the DocType's own permissions (see arrival_and_deployment.json),
	which now grants Transportation Manager a real base read/write role-permission
	on this doctype plus a permlevel 1 grant scoped to just this field -- so
	confirm_arrival() (see arrival_acknowledgement.py) can flip workflow_state to
	Joined/Did Not Arrive on their behalf without ignore_permissions. Every other
	role that already writes this field (System Manager, HR Manager, HR User,
	Recruitment Manager, Recruiter, Senior Recruiter, Interviewer) gets the
	matching permlevel 1 grant too, so this is additive-only for them.
	"""
	if not frappe.db.exists("Custom Field", "Arrival and Deployment-workflow_state"):
		return

	frappe.db.set_value("Custom Field", "Arrival and Deployment-workflow_state", "permlevel", 1)
	frappe.clear_cache(doctype="Arrival and Deployment")
