import frappe
from frappe.utils import now

DOCTYPE = "Bonus Request"

# Requested by the business: these Bonus Requests are stuck mid-approval and
# must be closed out administratively. Values are the target workflow state
# and the docstatus that state maps to in the "Bonus Request" workflow.
#
#   Completed -> docstatus 1   (normally reached via Pending Payroll Officer
#                               + "Complete Processing")
#   Cancelled -> docstatus 2   (normally reached via Pending Payroll Officer
#                               + "Cancel")
#
# None of these documents sit in "Pending Payroll Officer", so there is no
# legal workflow transition to walk. frappe.model.workflow.apply_workflow()
# would raise WorkflowTransitionError, and doc.submit()/doc.cancel() would
# re-run validate() (including validate_effective_month(), which now rejects
# the older effective months on these records). The state and docstatus are
# therefore written straight to the database, and the side effects the
# workflow would normally produce are cleaned up explicitly below.
TARGETS = {
	# Cancel
	"BR-2026-0243": "Cancelled",
	"BR-2026-0282": "Cancelled",
	# Mark as Completed
	"BR-2026-0257": "Completed",
	"BR-2026-0259": "Completed",
	"BR-2026-0260": "Completed",
	"BR-2026-0268": "Completed",
	"BR-2026-0270": "Completed",
	"BR-2026-0275": "Completed",
	"BR-2026-0276": "Completed",
}

STATE_DOCSTATUS = {
	"Completed": 1,
	"Cancelled": 2,
}


def execute():
	"""Force-close stale Bonus Requests to Completed / Cancelled.

	Writes workflow_state + docstatus directly (no workflow transition exists
	from the states these documents are parked in), then closes the open
	Workflow Actions and ToDos so the approvers' inboxes clear, and leaves a
	comment on each timeline for audit.
	"""
	if not frappe.db.table_exists("Bonus Request"):
		return

	for name, target_state in TARGETS.items():
		close_bonus_request(name, target_state)

	frappe.db.commit()


def close_bonus_request(name: str, target_state: str):
	current = frappe.db.get_value(
		DOCTYPE, name, ["workflow_state", "docstatus"], as_dict=True
	)

	if not current:
		print(f"[force_close_stale_bonus_requests] {name}: not found, skipped")
		return

	target_docstatus = STATE_DOCSTATUS[target_state]

	if current.workflow_state == target_state and current.docstatus == target_docstatus:
		print(f"[force_close_stale_bonus_requests] {name}: already {target_state}, skipped")
		return

	previous_state = current.workflow_state

	# Direct database write: bypasses the controller, the workflow engine and
	# the submit/cancel lifecycle by design.
	frappe.db.set_value(
		DOCTYPE,
		name,
		{
			"workflow_state": target_state,
			"docstatus": target_docstatus,
		},
		update_modified=False,
	)

	closed_actions = close_workflow_actions(name)
	closed_todos = close_todos(name)
	add_audit_comment(name, previous_state, target_state)

	print(
		f"[force_close_stale_bonus_requests] {name}: "
		f"{previous_state} (docstatus {current.docstatus}) -> "
		f"{target_state} (docstatus {target_docstatus}); "
		f"closed {closed_actions} workflow action(s), {closed_todos} todo(s)"
	)


def close_workflow_actions(name: str) -> int:
	"""Mark the pending Workflow Actions for this document as Completed.

	Mirrors what frappe.workflow...update_completed_workflow_actions() does
	after a real transition, so the document stops showing up as awaiting
	action for the previous approver.
	"""
	actions = frappe.get_all(
		"Workflow Action",
		filters={
			"reference_doctype": DOCTYPE,
			"reference_name": name,
			"status": "Open",
		},
		pluck="name",
	)

	for action in actions:
		frappe.db.set_value(
			"Workflow Action",
			action,
			{
				"status": "Completed",
				"completed_by": frappe.session.user,
			},
			update_modified=False,
		)

	return len(actions)


def close_todos(name: str) -> int:
	"""Close the open ToDos raised against this document.

	The assignment rules (Line Manager / HR Manager / General Manager /
	Finance Manager / Payroll Operator) leave these open; a closed document
	should not keep sitting in anyone's open assignment list.
	"""
	todos = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": DOCTYPE,
			"reference_name": name,
			"status": "Open",
		},
		pluck="name",
	)

	for todo in todos:
		frappe.db.set_value("ToDo", todo, "status", "Closed", update_modified=False)

	return len(todos)


def add_audit_comment(name: str, previous_state: str, target_state: str):
	"""Leave a trace on the document timeline explaining the manual change."""
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": DOCTYPE,
			"reference_name": name,
			"content": (
				f"Workflow state changed administratively from "
				f"<b>{previous_state}</b> to <b>{target_state}</b> by patch "
				f"<code>force_close_stale_bonus_requests</code> on {now()}, "
				f"as requested by the business. No workflow transition exists "
				f"from {previous_state} to {target_state}."
			),
		}
	).insert(ignore_permissions=True)
