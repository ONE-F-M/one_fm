"""Calls the GRD documents make into their Processa lifecycle process.

The GRD lifecycles (Work Permit, Medical Insurance, Residency, PACI, PCC Attestation,
Fingerprint Appointment, Preparation, Residency Payment Request) run on Processa maps.
The code that creates, cancels or rejects these documents in bulk goes through the
process instead of setting workflow_state itself.
"""

import frappe
from frappe import _


def active_instance(doctype, name):
	return frappe.db.get_value(
		"BPMN Process Instance",
		{"context_doctype": doctype, "context_docname": name, "status": "Active"},
		"name",
	)


def complete_action(doc, action, task_name=None):
	"""Take `action` on the task the document's process is waiting on.

	Returns False when the document has no live process, so the caller can fall back.
	"""
	from one_bpmn.api.instance_api import complete_task

	instance = active_instance(doc.doctype, doc.name)
	if not instance:
		return False

	waiting = [
		row
		for row in frappe.get_doc("BPMN Process Instance", instance).active_tasks
		if row.status == "Waiting" and (not task_name or row.task_name == task_name)
	]
	if not waiting:
		return False

	complete_task(instance, waiting[0].task_id, frappe.as_json({"action": action}))
	return True


def cancel_processes(doctype, names, reason):
	"""Cancel the live process of each document and close the ToDos its tasks opened."""
	from one_bpmn.one_bpmn.doctype.bpmn_process_instance.assignment import (
		remove_frappe_assignment,
		split_users,
	)

	if not names:
		return

	for instance_name in frappe.get_all(
		"BPMN Process Instance",
		filters={"context_doctype": doctype, "context_docname": ["in", list(names)], "status": "Active"},
		pluck="name",
	):
		instance = frappe.get_doc("BPMN Process Instance", instance_name)
		for row in instance.active_tasks:
			if row.status != "Waiting":
				continue
			row.status = "Cancelled"
			for user in split_users(row.assigned_user or ""):
				remove_frappe_assignment(instance, user, status="Cancelled")
		instance.status = "Cancelled"
		instance.log_operator_action("Cancelled", reason)
		instance.save(ignore_permissions=True)


def cancel_document(doc, reason):
	"""Cancel a submitted document whose lifecycle Processa owns.

	The engine refuses a native cancel on a Processa doctype, so the process is
	cancelled first and the cancel runs the way the engine runs its own.
	"""
	cancel_processes(doc.doctype, [doc.name], reason)
	previous = frappe.flags.bpmn_engine_action
	frappe.flags.bpmn_engine_action = True
	try:
		doc.cancel()
	finally:
		frappe.flags.bpmn_engine_action = previous


def retire_workflow(doctype, workflow, assignment_rules):
	"""Hand a doctype's lifecycle to its Processa map.

	The map drives every state change and assigns every task, so the Workflow and its
	assignment rules are switched off. Records already open are moved onto the map by
	Processa Legacy Migration.
	"""
	if workflow and frappe.db.exists("Workflow", workflow):
		frappe.db.set_value("Workflow", workflow, "is_active", 0)
		frappe.cache.hdel("workflow", doctype)

	for name in assignment_rules:
		if frappe.db.exists("Assignment Rule", name):
			frappe.db.set_value("Assignment Rule", name, "disabled", 1)

	frappe.clear_cache(doctype=doctype)
