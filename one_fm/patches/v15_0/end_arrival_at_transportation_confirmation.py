"""Arrival and Deployment ends with Onboarding Confirmed, the Transportation Manager's pickup and Arrived or Did Not Arrive; support department acknowledgements are removed."""

import frappe

from one_fm.custom.workflow.workflow import create_workflow_action_master, create_workflow_state

OVERSEAS = "doc.candidate_country_process"
LOCAL = "not doc.candidate_country_process"
# state, style, role that may edit the form in it; the Transportation Manager types the driver in Onboarding Confirmed
NEW_STATES = (
	("Onboarding Confirmed", "Primary", "Onboarding Officer"),
	("Onboarding Confirmed", "Primary", "Transportation Manager"),
	("Pick Up Arranged", "Info", "Transportation Manager"),
	("Arrived", "Success", "Transportation Manager"),
)
# state, action, next state, role, condition
TRANSITIONS = [
	("Pending Onboarding", "Confirm Onboarding", "Onboarding Confirmed", "Onboarding Officer", ""),
	("Pending Onboarding", "Confirm Onboarding", "Onboarding Confirmed", "System Manager", ""),
	("Onboarding Confirmed", "Arrange Pick Up", "Pick Up Arranged", "Transportation Manager", OVERSEAS),
	("Onboarding Confirmed", "Arrange Pick Up", "Pick Up Arranged", "System Manager", OVERSEAS),
]
for outcome in ("Arrived", "Did Not Arrive"):
	TRANSITIONS += [
		("Onboarding Confirmed", outcome, outcome, "Onboarding Officer", LOCAL),
		("Onboarding Confirmed", outcome, outcome, "System Manager", LOCAL),
		("Pick Up Arranged", outcome, outcome, "Transportation Manager", ""),
		("Pick Up Arranged", outcome, outcome, "System Manager", ""),
		("Pending Support Departments", outcome, outcome, "Transportation Manager", OVERSEAS),
		("Pending Support Departments", outcome, outcome, "Onboarding Officer", LOCAL),
		("Pending Support Departments", outcome, outcome, "System Manager", ""),
	]
REPLACED_ACTIONS = {"Submit to Support Departments", "Mark as Joined"} | {t[1] for t in TRANSITIONS}


def execute():
	end_workflow_at_arrival()
	remove_arrival_acknowledgements()
	keep_only_the_onboarding_mailbox()


def end_workflow_at_arrival():
	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		return

	create_workflow_state([{"workflow_state_name": state, "style": style} for state, style, _ in NEW_STATES])
	create_workflow_action_master(["Confirm Onboarding", "Arrange Pick Up", "Arrived", "Did Not Arrive"])

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
	existing_states = {(d.state, d.allow_edit) for d in workflow.states}
	for state, _, allow_edit in NEW_STATES:
		if (state, allow_edit) not in existing_states:
			workflow.append("states", {"state": state, "doc_status": "0", "allow_edit": allow_edit})

	workflow.transitions = [t for t in workflow.transitions if t.action not in REPLACED_ACTIONS]
	for state, action, next_state, role, condition in TRANSITIONS:
		workflow.append(
			"transitions",
			{
				"state": state,
				"action": action,
				"next_state": next_state,
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
