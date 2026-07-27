import frappe


def execute():
	"""Add Transportation Manager as an allowed role for the "Mark as Joined" and
	"Did Not Arrive" transitions on the Arrival and Deployment workflow.

	confirm_arrival() (see arrival_acknowledgement.py) drives these transitions on
	Transportation Manager's behalf via a plain doc.save(), not
	frappe.model.workflow.apply_workflow() -- but Frappe's own Document._validate()
	unconditionally runs validate_workflow() on every save when a Workflow exists
	for the doctype, which calls get_transitions() and filters to transitions whose
	"allowed" role the current user actually holds. Without this patch, that filter
	drops both transitions for Transportation Manager (only Onboarding Officer and
	System Manager were ever listed), so the save would still fail even with a real
	role-permission grant on the doctype -- pairs with the has_permission() scoping
	and permlevel grant added alongside it.

	Deliberately additive only, same as the earlier workflow patches for this
	doctype: only appends the missing transition rows, never touches what's
	already there.
	"""
	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		return

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")

	new_transitions = [
		("Pending Support Departments", "Mark as Joined", "Joined", "Transportation Manager"),
		("Pending Support Departments", "Did Not Arrive", "Did Not Arrive", "Transportation Manager"),
	]

	existing_transitions = {
		(t.state, t.action, t.next_state, t.allowed) for t in workflow.transitions
	}
	changed = False
	for state, action, next_state, allowed in new_transitions:
		if (state, action, next_state, allowed) not in existing_transitions:
			workflow.append("transitions", {
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": allowed,
			})
			changed = True

	if changed:
		workflow.flags.ignore_mandatory = True
		workflow.save()
		frappe.clear_cache(doctype="Arrival and Deployment")
