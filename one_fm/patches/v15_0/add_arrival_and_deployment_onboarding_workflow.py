import frappe
from one_fm.custom.workflow.workflow import create_workflow_state, create_workflow_action_master


def execute():
	"""Add the "Submit to Onboarding" transition (Draft -> Pending Onboarding) to the
	Arrival and Deployment workflow.

	Deliberately additive only: if a workflow already exists for this doctype (it may
	already have states/transitions for Pending Support Departments, Joined, Did Not
	Arrive etc. that this patch has no knowledge of), only appends the state/transition
	needed for the new "Submit to Onboarding" step if missing — never replaces or
	overwrites the existing states/transitions list. If no workflow exists yet at all,
	creates a minimal one with just these two states and this one transition.
	"""
	create_workflow_state([
		{"workflow_state_name": "Draft", "style": "Primary"},
		{"workflow_state_name": "Pending Onboarding", "style": "Warning"},
	])
	create_workflow_action_master(["Submit to Onboarding"])

	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		frappe.get_doc({
			"doctype": "Workflow",
			"workflow_name": "Arrival and Deployment",
			"document_type": "Arrival and Deployment",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{"state": "Draft", "doc_status": "0", "allow_edit": "Recruiter"},
				{"state": "Pending Onboarding", "doc_status": "0", "allow_edit": "Recruiter"},
			],
			"transitions": [
				{
					"state": "Draft",
					"action": "Submit to Onboarding",
					"next_state": "Pending Onboarding",
					"allowed": "Recruiter",
				},
			],
		}).insert()
		return

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")

	existing_states = {s.state for s in workflow.states}
	for state, allow_edit in [("Draft", "Recruiter"), ("Pending Onboarding", "Recruiter")]:
		if state not in existing_states:
			workflow.append("states", {
				"state": state,
				"doc_status": "0",
				"allow_edit": allow_edit,
			})

	has_transition = any(
		t.state == "Draft" and t.action == "Submit to Onboarding" and t.next_state == "Pending Onboarding"
		for t in workflow.transitions
	)
	if not has_transition:
		workflow.append("transitions", {
			"state": "Draft",
			"action": "Submit to Onboarding",
			"next_state": "Pending Onboarding",
			"allowed": "Recruiter",
		})

	workflow.flags.ignore_mandatory = True
	workflow.save()
	frappe.clear_cache(doctype="Arrival and Deployment")
