import frappe
from frappe.desk.form.assign_to import close_all_assignments
from frappe.utils import now

LOG = "[close_stranded_legacy_ojt_requests]"
DOCTYPE = "On the Job Training"

# HD-1900434. On 2026-10-18 14:54:51 the patch move_ojt_lifecycle_to_processa handed the OJT
# lifecycle to the Processa process map: it set the "On the Job Training" Workflow to
# is_active = 0 and disabled the Assignment Rules "Assigning Project Manager for Approval"
# and "Returning to Operations Supervisor of OJT Request". In-flight records were not
# drained, and these two are stranded by it:
#
#   * with the workflow inactive the form renders no Approve / Reject / Return To Draft
#     action and frappe.model.workflow.apply_workflow() raises WorkflowTransitionError,
#     so there is no legal transition out of "Pending Approval";
#   * the first BPMN Process Instance is for OJT-10-2026-0045 (2026-10-19 20:08) - these
#     two have none, so the process map will never pick them up either;
#   * the disabled Assignment Rules can never fire their unassign_condition
#     (workflow_state != "Pending Approval"), so the ToDo and _assign never clear.
#
# Both trainings were delivered: the Employee Schedules with employee_availability =
# "On-the-job Training" already exist (OJT-10-2026-0020: 5 days, 2026-10-10 to 2026-10-14;
# OJT-10-2026-0035: 6 days, 2026-10-14 to 2026-10-19). Only the approval record is stuck,
# so "Approved" - docstatus 1 in the OJT workflow - is the state they should have reached.
#
# The state is written straight to the database. doc.submit() would re-run validate()
# (validate_dates / validate_annual_leave_conflict) against dates that are now in the past,
# and the OJT controller defines no on_submit while hooks.py registers no doc_events for the
# doctype, so there are no submit side effects to reproduce beyond the assignments closed
# below. The Employee Schedules already exist and are deliberately left untouched.
#
# Same failure class as force_close_bonus_request_br_2026_0286 (HD-1903486), same cutover.
TARGETS = ("OJT-10-2026-0020", "OJT-10-2026-0035")
TARGET_STATE = "Approved"
TARGET_DOCSTATUS = 1


def execute():
	if not frappe.db.table_exists(DOCTYPE):
		return

	# Guard against TARGETS being edited down to a bare string: ("NAME") is not a tuple,
	# and iterating it would look up one character at a time.
	if isinstance(TARGETS, str):
		frappe.throw(f"{LOG} TARGETS must be a tuple of document names, not a string.")

	for name in TARGETS:
		close_stranded_request(name)

	frappe.db.commit()


def close_stranded_request(name: str):
	current = frappe.db.get_value(DOCTYPE, name, ["workflow_state", "docstatus"], as_dict=True)

	if not current:
		print(f"{LOG} {name}: not found, skipped")
		return

	if current.workflow_state == TARGET_STATE and current.docstatus == TARGET_DOCSTATUS:
		print(f"{LOG} {name}: already {TARGET_STATE}, skipped")
		return

	if current.docstatus == 2:
		# Cancelled by someone in the meantime: do not resurrect it.
		print(f"{LOG} {name}: cancelled (docstatus 2), skipped")
		return

	if has_process_instance(name):
		# Processa has adopted the record since this patch was written; let the map drive it.
		print(f"{LOG} {name}: has a BPMN Process Instance, skipped")
		return

	previous_state = current.workflow_state

	# Close the assignments first, while the document is still a draft.
	#
	# close_all_assignments() is used rather than flipping ToDo.status directly: it goes
	# through todo.save(), which fires ToDo.update_in_reference() and recomputes _assign on
	# the document from the remaining open ToDos. That second part is what actually drops
	# the record out of the "Assigned To" list view, and it matters here because the two
	# inboxes disagree - the open ToDo belongs to a.alazmi@one-fm.com (the Project Manager
	# at creation time) while _assign carries m.mothaffar@one-fm.com (where
	# route_ojt_to_project_manager later moved it). Closing only the ToDo would leave the
	# record sitting in m.mothaffar's list.
	closed_todos = close_all_assignments(DOCTYPE, name, ignore_permissions=True)
	closed_actions = close_workflow_actions(name)

	# Direct database write: bypasses the controller, the workflow engine and the submit
	# lifecycle by design (see the note at the top of this file).
	frappe.db.set_value(
		DOCTYPE,
		name,
		{
			"workflow_state": TARGET_STATE,
			"docstatus": TARGET_DOCSTATUS,
		},
		update_modified=False,
	)

	add_audit_comment(name, previous_state)

	print(
		f"{LOG} {name}: {previous_state} (docstatus {current.docstatus}) -> "
		f"{TARGET_STATE} (docstatus {TARGET_DOCSTATUS}); "
		f"assignments closed: {bool(closed_todos)}, "
		f"workflow action(s) closed: {closed_actions}, "
		f"_assign now {frappe.db.get_value(DOCTYPE, name, '_assign')!r}"
	)


def has_process_instance(name: str) -> bool:
	"""True when the Processa process map has taken this record over."""
	if not frappe.db.table_exists("BPMN Process Instance"):
		return False

	return bool(
		frappe.db.exists(
			"BPMN Process Instance",
			{"context_doctype": DOCTYPE, "context_docname": name},
		)
	)


def close_workflow_actions(name: str) -> int:
	"""Mark the pending Workflow Actions for this document as Completed.

	Mirrors what frappe.workflow...update_completed_workflow_actions() does after a real
	transition. Neither target has an open Workflow Action today; this keeps the patch
	correct if one is raised before it runs.
	"""
	actions = frappe.get_all(
		"Workflow Action",
		filters={"reference_doctype": DOCTYPE, "reference_name": name, "status": "Open"},
		pluck="name",
	)

	for action in actions:
		frappe.db.set_value(
			"Workflow Action",
			action,
			{"status": "Completed", "completed_by": frappe.session.user},
			update_modified=False,
		)

	return len(actions)


def add_audit_comment(name: str, previous_state: str):
	"""Leave a trace on the document timeline explaining the manual change."""
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": DOCTYPE,
			"reference_name": name,
			"content": (
				f"Workflow state changed administratively from <b>{previous_state}</b> to "
				f"<b>{TARGET_STATE}</b> by patch "
				f"<code>close_stranded_legacy_ojt_requests</code> on {now()}, as requested "
				f"in HD-1900434. The training was delivered - the Employee Schedules for it "
				f"already exist - but the On the Job Training workflow was deactivated on "
				f"2026-10-18 by move_ojt_lifecycle_to_processa, so no transition out of "
				f"{previous_state} remained and the request could not be approved. The open "
				f"assignments on this record were closed at the same time."
			),
		}
	).insert(ignore_permissions=True)
