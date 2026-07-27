import frappe


def execute():
	"""For corporate (is_corporate=1) resignation withdrawals, the Line
	Manager's Accept/Reject decision is now final -- no Operations Manager
	step at all, matching Employee Resignation's own corporate path (direct
	Pending Supervisor -> Approved, condition shift_working == 0).

	Shift workers are unaffected: Accept/Reject still route through
	Accepted by Supervisor / Rejected By Supervisor for Operations Manager
	to give the final sign-off.

	Gates the two existing employee-facing transitions on `not doc.is_corporate`
	so they only fire for shift workers now that direct transitions exist for
	corporate employees, and adds two new transitions straight to the
	terminal state, gated on `doc.is_corporate`.

	validate_rejection_reason() in the controller already checks old/new
	workflow_state VALUES (not which specific transition path was taken), so
	Reason for Rejection is still correctly required on the new direct
	Reject transition without any code changes there.
	Both the existing and the new transitions carry allowed_user_field=
	"supervisor", matching the original access-control model exactly: only
	the specific Line Manager/Supervisor recorded on the document -- not just
	any user holding the Employee role -- can act on it, corporate or not.
	"""
	workflow_name = "Employee Resignation Withdrawal"
	if not frappe.db.exists("Workflow", workflow_name):
		return

	workflow = frappe.get_doc("Workflow", workflow_name)
	changed = False

	# Gate the existing shift-worker transitions.
	for t in workflow.transitions:
		if (
			t.state == "Pending Supervisor"
			and t.action == "Accept"
			and t.next_state == "Accepted by Supervisor"
			and not t.condition
		):
			t.condition = "not doc.is_corporate"
			changed = True
		if (
			t.state == "Pending Supervisor"
			and t.action == "Reject"
			and t.next_state == "Rejected By Supervisor"
			and not t.condition
		):
			t.condition = "not doc.is_corporate"
			changed = True

	# Add the new direct-to-terminal transitions for corporate employees.
	# allowed_user_field="supervisor" matches the existing transitions'
	# access control exactly -- only the recorded Line Manager can act.
	new_transitions = [
		("Pending Supervisor", "Accept", "Approved", "Employee", "doc.is_corporate"),
		("Pending Supervisor", "Reject", "Rejected", "Employee", "doc.is_corporate"),
	]
	for state, action, next_state, allowed, condition in new_transitions:
		existing = next(
			(t for t in workflow.transitions
				if t.state == state and t.action == action and t.next_state == next_state and t.allowed == allowed),
			None,
		)
		if existing:
			if existing.allowed_user_field != "supervisor":
				existing.allowed_user_field = "supervisor"
				changed = True
		else:
			workflow.append("transitions", {
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": allowed,
				"condition": condition,
				"allowed_user_field": "supervisor",
			})
			changed = True

	if changed:
		workflow.flags.ignore_mandatory = True
		workflow.save()

	frappe.clear_cache(doctype=workflow.document_type)
