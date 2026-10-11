"""Let the Onboarding Officer, as well as the Recruiter, edit Arrival and Deployment in Pending Onboarding."""

import frappe


def execute():
	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		return

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
	editors = {d.allow_edit for d in workflow.states if d.state == "Pending Onboarding"}
	if "Onboarding Officer" in editors:
		return

	workflow.append(
		"states", {"state": "Pending Onboarding", "doc_status": "0", "allow_edit": "Onboarding Officer"}
	)
	workflow.save()
