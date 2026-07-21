import frappe


def execute():
	"""Employee Resignation Withdrawal's "Approve" transitions (from both "Accepted by
	Supervisor" and "Rejected By Supervisor") were restricted via allowed_user_field to
	the one specific Operations Manager recorded on the document (see one_fm.overrides.
	workflow.get_specific_user, this app's custom override of Frappe's workflow engine) --
	meaning any OTHER Operations Manager couldn't see or use the Approve button at all,
	even though the role-level "allowed" already said "Operations Manager".

	Clears allowed_user_field on just those two transitions so any user holding the
	Operations Manager role can approve, matching how the main Employee Resignation
	workflow's own "Pending Operations Manager -> Approve" transition already works
	(role-only, no specific-user restriction). The "Reject" transitions on the same two
	states keep their existing allowed_user_field restriction untouched -- only Approve
	was in scope for this change.

	Deliberately does not call create_workflow() / workflow.update() for this: that
	replaces the live workflow's states/transitions wholesale from the checked-in JSON,
	which risks clobbering any production-only drift unrelated to this fix. This only
	touches the exact two Workflow Transition rows in question, on the already-loaded
	live document, leaving everything else exactly as it was.
	"""
	workflow_name = "Employee Resignation Withdrawal"
	if not frappe.db.exists("Workflow", workflow_name):
		return

	workflow = frappe.get_doc("Workflow", workflow_name)
	changed = False
	for transition in workflow.transitions:
		if (
			transition.action == "Approve"
			and transition.allowed == "Operations Manager"
			and transition.allowed_user_field
		):
			transition.allowed_user_field = None
			changed = True

	if changed:
		workflow.flags.ignore_mandatory = True
		workflow.save(ignore_permissions=True)

	frappe.clear_cache(doctype="Employee Resignation Withdrawal")
