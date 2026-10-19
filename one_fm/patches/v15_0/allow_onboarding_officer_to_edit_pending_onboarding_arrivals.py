"""Let the Onboarding Officer, as well as the Recruiter, edit Arrival and Deployment in Pending Onboarding."""

import frappe


def execute():
	if not frappe.db.exists("Workflow", "Arrival and Deployment"):
		return

	workflow = frappe.get_doc("Workflow", "Arrival and Deployment")
	pending_onboarding = [d for d in workflow.states if d.state == "Pending Onboarding"]
	if not pending_onboarding or "Onboarding Officer" in {d.allow_edit for d in pending_onboarding}:
		return

	onboarding_officer_row = pending_onboarding[0].as_dict(no_default_fields=True)
	onboarding_officer_row["allow_edit"] = "Onboarding Officer"
	workflow.append("states", onboarding_officer_row)
	workflow.save()
