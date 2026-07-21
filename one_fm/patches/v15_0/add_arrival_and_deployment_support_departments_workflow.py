import frappe
from one_fm.custom.workflow.workflow import create_workflow_state, create_workflow_action_master


def execute():
	"""Add the "Submit to Support Departments", "Mark as Joined", and "Did Not Arrive"
	transitions to the Arrival and Deployment workflow.

	The earlier patch (add_arrival_and_deployment_onboarding_workflow) only ever wired
	up the first hop (Draft -> Submit to Onboarding -> Pending Onboarding). Code added
	afterward -- assign_support_departments(), the Joined/Did Not Arrive checks in
	validate(), the confirm_arrival() flow on Arrival Acknowledgement -- all assume
	Pending Support Departments/Joined/Did Not Arrive states exist, but nothing had
	ever added them to the real Workflow record, so those transitions were reachable
	by no one.

	Deliberately additive only, same as the earlier patch: only appends states/
	transitions that are missing, never touches what's already there.
	"""
	create_workflow_state([
		{"workflow_state_name": "Pending Support Departments", "style": "Warning"},
		{"workflow_state_name": "Joined", "style": "Success"},
		{"workflow_state_name": "Did Not Arrive", "style": "Danger"},
	])
	create_workflow_action_master(["Submit to Support Departments", "Mark as Joined", "Did Not Arrive"])

	new_states = [
		("Pending Support Departments", "Onboarding Officer"),
		("Joined", "Onboarding Officer"),
		("Did Not Arrive", "Onboarding Officer"),
	]
	new_transitions = [
		("Pending Onboarding", "Submit to Support Departments", "Pending Support Departments", "Onboarding Officer"),
		("Pending Onboarding", "Submit to Support Departments", "Pending Support Departments", "System Manager"),
		("Pending Support Departments", "Mark as Joined", "Joined", "Onboarding Officer"),
		("Pending Support Departments", "Mark as Joined", "Joined", "System Manager"),
		("Pending Support Departments", "Did Not Arrive", "Did Not Arrive", "Onboarding Officer"),
		("Pending Support Departments", "Did Not Arrive", "Did Not Arrive", "System Manager"),
	]

	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		# Shouldn't happen -- the earlier patch always creates this -- but handle it
		# the same additive way if it's ever run against an environment where it's missing.
		frappe.get_doc({
			"doctype": "Workflow",
			"workflow_name": "Arrival and Deployment",
			"document_type": "Arrival and Deployment",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [{"state": s, "doc_status": "0", "allow_edit": a} for s, a in new_states],
			"transitions": [
				{"state": s, "action": a, "next_state": ns, "allowed": r}
				for s, a, ns, r in new_transitions
			],
		}).insert(ignore_permissions=True)
		return

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")

	existing_states = {s.state for s in workflow.states}
	for state, allow_edit in new_states:
		if state not in existing_states:
			workflow.append("states", {
				"state": state,
				"doc_status": "0",
				"allow_edit": allow_edit,
			})

	existing_transitions = {
		(t.state, t.action, t.next_state, t.allowed) for t in workflow.transitions
	}
	for state, action, next_state, allowed in new_transitions:
		if (state, action, next_state, allowed) not in existing_transitions:
			workflow.append("transitions", {
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": allowed,
			})

	workflow.flags.ignore_mandatory = True
	workflow.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Arrival and Deployment")
