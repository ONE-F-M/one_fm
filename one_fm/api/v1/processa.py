import json

import frappe
from frappe import _
from frappe.utils import get_fullname

from one_fm.api.v1.utils import handle_attachment_internal


@frappe.whitelist(methods=["GET"])
def get_document_actions(doctype: str, docname: str) -> dict:
	"""The Processa actions the session user can take on a document, and who holds the other waiting tasks."""
	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("read")
	return _document_actions(doc)


@frappe.whitelist(methods=["POST"])
def apply_document_action(
	doctype: str,
	docname: str,
	task_id: str,
	action: str,
	values: str | dict | None = None,
	attachments: str | dict | None = None,
) -> dict:
	"""Save the fields the current step allows, then complete the Processa task with the action."""
	from one_bpmn.api.instance_api import complete_task

	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("read")
	task = _find_task(doc, task_id, action)
	_save_editable_fields(doc, frappe.parse_json(values or {}), frappe.parse_json(attachments or {}))
	result = complete_task(task["instance_name"], task_id, json.dumps({"action": action} if action else {}))
	doc.reload()
	return {
		**_document_actions(doc),
		"process_status": result["status"],
		"messages": [message.get("message") for message in frappe.get_message_log()],
	}


def _document_actions(doc) -> dict:
	from one_bpmn.api.instance_api import get_active_bpmn_tasks
	from one_bpmn.one_bpmn.doctype.bpmn_process_instance.assignment import split_users

	actions, pending_with = [], []
	for task in get_active_bpmn_tasks(doc.doctype, doc.name):
		if not task["can_action"]:
			holders = [get_fullname(user) for user in split_users(task["assigned_user"])]
			pending_with.extend(holders or [task["assigned_role"]])
			continue

		# A task with no configured actions completes with a single confirmed button, as on the desk form
		details = [detail for detail in task["task_actions_detail"] if detail.get("action")]
		for detail in details or [{"action": "", "confirmTransition": "true"}]:
			actions.append(
				{
					"instance_name": task["instance_name"],
					"task_id": task["task_id"],
					"task_name": task["task_name"],
					"action": detail["action"],
					"confirm": detail.get("confirmTransition") == "true",
				}
			)

	return {
		"workflow_state": doc.get("workflow_state"),
		"actions": actions,
		"pending_with": pending_with,
		"editable_fields": _editable_fields(doc),
	}


def _find_task(doc, task_id: str, action: str) -> dict:
	task = next(
		(a for a in _document_actions(doc)["actions"] if a["task_id"] == task_id and a["action"] == action),
		None,
	)
	if not task:
		frappe.throw(_("This action is no longer available. Refresh and try again."), frappe.PermissionError)
	return task


def _save_editable_fields(doc, values: dict, attachments: dict) -> None:
	if not values and not attachments:
		return

	refused = sorted((set(values) | set(attachments)) - set(_editable_fields(doc)))
	if refused:
		labels = ", ".join(_(doc.meta.get_label(fieldname) or fieldname) for fieldname in refused)
		frappe.throw(_("You cannot change {0} at this step.").format(labels), frappe.PermissionError)

	doc.check_permission("write")
	doc.update(values)
	doc.save()
	for fieldname, attachment in attachments.items():
		handle_attachment_internal(doc, doc, attachment, fieldname)


def _editable_fields(doc) -> list:
	get_editable_fields = getattr(doc, "get_processa_editable_fields", None)
	return get_editable_fields() if get_editable_fields else []
