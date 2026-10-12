"""Arrival and Deployment ends with Onboarding Confirmed then Arrived or Did Not Arrive; support department acknowledgements are removed."""

import frappe

from one_fm.custom.workflow.workflow import create_workflow_action_master, create_workflow_state

REMOVED_ACTIONS = ("Submit to Support Departments", "Mark as Joined", "Did Not Arrive", "Arrived")
OVERSEAS = "doc.candidate_country_process"
LOCAL = "not doc.candidate_country_process"
ARRIVAL_ROLES = (("Transportation Manager", OVERSEAS), ("Onboarding Officer", LOCAL), ("System Manager", ""))


def execute():
	end_workflow_at_arrival()
	remove_arrival_acknowledgements()
	keep_only_the_onboarding_mailbox()


def end_workflow_at_arrival():
	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		return

	create_workflow_state(
		[
			{"workflow_state_name": "Onboarding Confirmed", "style": "Primary"},
			{"workflow_state_name": "Arrived", "style": "Success"},
		]
	)
	create_workflow_action_master(["Confirm Onboarding", "Arrived", "Did Not Arrive"])

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
	existing_states = {d.state for d in workflow.states}
	for state, allow_edit in (
		("Onboarding Confirmed", "Onboarding Officer"),
		("Arrived", "Transportation Manager"),
	):
		if state not in existing_states:
			workflow.append("states", {"state": state, "doc_status": "0", "allow_edit": allow_edit})

	workflow.transitions = [
		t for t in workflow.transitions if t.action not in REMOVED_ACTIONS + ("Confirm Onboarding",)
	]
	for role in ("Onboarding Officer", "System Manager"):
		workflow.append(
			"transitions",
			{
				"state": "Pending Onboarding",
				"action": "Confirm Onboarding",
				"next_state": "Onboarding Confirmed",
				"allowed": role,
			},
		)
	for state in ("Onboarding Confirmed", "Pending Support Departments"):
		for action in ("Arrived", "Did Not Arrive"):
			for role, condition in ARRIVAL_ROLES:
				workflow.append(
					"transitions",
					{
						"state": state,
						"action": action,
						"next_state": action,
						"allowed": role,
						"condition": condition,
					},
				)
	workflow.save()


def remove_arrival_acknowledgements():
	frappe.db.set_value(
		"ToDo", {"reference_type": "Arrival Acknowledgement", "status": "Open"}, "status", "Cancelled"
	)
	frappe.db.delete("Custom DocPerm", {"parent": "Arrival Acknowledgement"})
	for doctype in ("Assignment Rule", "Workflow"):
		for name in frappe.get_all(
			doctype, filters={"document_type": "Arrival Acknowledgement"}, pluck="name"
		):
			frappe.delete_doc(doctype, name)
	frappe.delete_doc("DocType", "Arrival Acknowledgement", ignore_missing=True, force=True)
	# Deleting a DocType keeps its table; the installer drops tables the same way
	frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabArrival Acknowledgement`")


def keep_only_the_onboarding_mailbox():
	frappe.db.delete(
		"Arrival Department Email", {"parenttype": "Hiring Settings", "department": ["!=", "Onboarding"]}
	)
