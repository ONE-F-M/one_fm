"""WI-002608: "Visa Cancellation Rejected" is now "Rejected by PRO".

The rename comes from the BA site's process map. The map itself is imported separately;
what this patch does is stop the rows already in the system being left behind by it.

Why it matters, in the words the controller already used before this was the live case:
is_standing() decides whether a refused cancellation still blocks its Visa Request from
being cancelled again, and it decides it by comparing against this one string. A row still
holding the old name would compare unequal to the new one, so every cancellation the PRO
Operator has ALREADY refused would read as still standing, and its Visa Request could
never be cancelled again. Four rows are in that state.

The old Workflow State record is deliberately left in place. No workflow references it -
checked across every Workflow on the site - and deleting a master that historical records
and Version rows still name buys nothing.
"""

import frappe

OLD_STATE = "Visa Cancellation Rejected"
NEW_STATE = "Rejected by PRO"
DOCTYPE = "Visa Cancellation Request"


def execute():
	ensure_workflow_state()

	if not frappe.db.has_column(DOCTYPE, "workflow_state"):
		# The column only exists once a workflow has been attached. Nothing holds a state
		# yet, so nothing needs moving.
		return

	frappe.db.set_value(
		DOCTYPE, {"workflow_state": OLD_STATE}, "workflow_state", NEW_STATE,
		update_modified=False,
	)


def ensure_workflow_state():
	"""The imported process map brings this state with it, but the rows are renamed here.

	Creating it first keeps the two in step whichever order they land in - a workflow_state
	pointing at a Workflow State that does not exist is a broken link on every one of those
	documents.
	"""
	if frappe.db.exists("Workflow State", NEW_STATE):
		return

	style = frappe.db.get_value("Workflow State", OLD_STATE, "style") or "Danger"
	frappe.get_doc({
		"doctype": "Workflow State",
		"workflow_state_name": NEW_STATE,
		"style": style,
	}).insert(ignore_permissions=True)
