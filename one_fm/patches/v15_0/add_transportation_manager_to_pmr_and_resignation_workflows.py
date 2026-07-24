import frappe


def execute():
	"""Additive-only: add Transportation Manager to the same workflow states/transitions
	Operation Admin/T4 Admin already have on Project Manpower Request and Employee
	Resignation, without touching anything else already configured on either live
	Workflow document.

	This app stores allow_edit as one Workflow Document State row per (state, role)
	pair rather than a single comma-separated value -- confirmed directly against the
	live Workflow documents, where e.g. "Draft" already has separate rows for Employee,
	Recruiter, Operation Admin, etc. Same for Workflow Transition: multiple rows share
	the same (state, action, next_state) with a different "allowed" role each.
	"""
	_add_role_to_workflow(
		"Project Manpower Request",
		allow_edit_states=["Draft", "In Process"],
		transitions=[
			("Draft", "Submit to Recruiter", "Awaiting Recruiter Approval"),
			("In Process", "Complete", "Completed"),
			("In Process", "Request Edit", "Draft"),
		],
		role="Transportation Manager",
	)

	_add_role_to_workflow(
		"Employee Resignation",
		allow_edit_states=["Pending Operations Manager"],
		transitions=[],
		role="Transportation Manager",
	)


def _add_role_to_workflow(workflow_name, allow_edit_states, transitions, role):
	if not frappe.db.exists("Workflow", workflow_name):
		return

	workflow = frappe.get_doc("Workflow", workflow_name)
	changed = False

	for state in allow_edit_states:
		already_has_role = any(s.state == state and s.allow_edit == role for s in workflow.states)
		if already_has_role:
			continue
		existing_doc_status = next((s.doc_status for s in workflow.states if s.state == state), "0")
		workflow.append("states", {
			"state": state,
			"doc_status": existing_doc_status,
			"allow_edit": role,
		})
		changed = True

	for state, action, next_state in transitions:
		already_has_role = any(
			t.state == state and t.action == action and t.next_state == next_state and t.allowed == role
			for t in workflow.transitions
		)
		if already_has_role:
			continue
		workflow.append("transitions", {
			"state": state,
			"action": action,
			"next_state": next_state,
			"allowed": role,
			"allow_self_approval": 1,
		})
		changed = True

	if changed:
		workflow.flags.ignore_mandatory = True
		workflow.save()

	frappe.clear_cache(doctype=workflow.document_type)
