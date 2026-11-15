import frappe
from frappe.utils import now

from one_fm.patches.v15_0.force_close_stale_bonus_requests import (
	DOCTYPE,
	STATE_DOCSTATUS,
	close_todos,
	close_workflow_actions,
)

LOG = "[force_close_bonus_request_br_2026_0286]"

# HD-1903486. BR-2026-0286 was approved by the HR Manager on 2026-09-28 and has
# sat in "Pending General Manager" ever since. On 2026-10-18 the patch
# deactivate_bonus_request_workflow_and_assignment_rules set the "Bonus Request"
# Workflow to is_active = 0 (the Processa process map took over), so the document
# no longer renders any workflow action and there is no legal transition left to
# walk: frappe.model.workflow.apply_workflow() would raise WorkflowTransitionError
# and, with the workflow inactive, doc.submit() would set docstatus 1 while
# leaving workflow_state on "Pending General Manager".
#
# The bonus itself has already been paid through payroll, so the business asked
# for the record to be closed out administratively. Same treatment as the nine
# records handled by force_close_stale_bonus_requests on 2026-10-01; this one was
# simply not on that list.
#
# "Completed" maps to docstatus 1 in the Bonus Request workflow. The Bonus Request
# controller defines no on_submit and hooks.py registers no doc_events for the
# doctype, so writing the state directly has no submit side effects to reproduce
# beyond the Workflow Actions and ToDos closed below.
TARGET = "BR-2026-0286"
TARGET_STATE = "Completed"


def execute():
	if not frappe.db.table_exists(DOCTYPE):
		return

	current = frappe.db.get_value(
		DOCTYPE, TARGET, ["workflow_state", "docstatus"], as_dict=True
	)

	if not current:
		print(f"{LOG} {TARGET}: not found, skipped")
		return

	target_docstatus = STATE_DOCSTATUS[TARGET_STATE]

	if current.workflow_state == TARGET_STATE and current.docstatus == target_docstatus:
		print(f"{LOG} {TARGET}: already {TARGET_STATE}, skipped")
		return

	if current.docstatus == 2:
		# Cancelled by someone in the meantime: do not resurrect it.
		print(f"{LOG} {TARGET}: cancelled (docstatus 2), skipped")
		return

	previous_state = current.workflow_state

	# Direct database write: bypasses the controller, the workflow engine and the
	# submit lifecycle by design (see the note above).
	frappe.db.set_value(
		DOCTYPE,
		TARGET,
		{
			"workflow_state": TARGET_STATE,
			"docstatus": target_docstatus,
		},
		update_modified=False,
	)

	closed_actions = close_workflow_actions(TARGET)
	closed_todos = close_todos(TARGET)
	add_audit_comment(previous_state)

	print(
		f"{LOG} {TARGET}: {previous_state} (docstatus {current.docstatus}) -> "
		f"{TARGET_STATE} (docstatus {target_docstatus}); "
		f"closed {closed_actions} workflow action(s), {closed_todos} todo(s)"
	)

	frappe.db.commit()


def add_audit_comment(previous_state: str):
	"""Leave a trace on the document timeline explaining the manual change."""
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": DOCTYPE,
			"reference_name": TARGET,
			"content": (
				f"Workflow state changed administratively from "
				f"<b>{previous_state}</b> to <b>{TARGET_STATE}</b> by patch "
				f"<code>force_close_bonus_request_br_2026_0286</code> on {now()}, "
				f"as requested by the business in HD-1903486 (the bonus was already "
				f"processed through payroll). The Bonus Request workflow is inactive, "
				f"so no transition exists from {previous_state} to {TARGET_STATE}."
			),
		}
	).insert(ignore_permissions=True)
