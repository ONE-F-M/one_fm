"""Candidate Country Processes still In Process whose arrival is already with onboarding move to Arriving."""

import frappe

from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import SUBMITTED_STATES


def execute():
	ccp_names = frappe.get_all(
		"Arrival and Deployment",
		filters={"workflow_state": ["in", SUBMITTED_STATES], "candidate_country_process": ["is", "set"]},
		pluck="candidate_country_process",
	)
	for ccp_name in frappe.get_all(
		"Candidate Country Process",
		filters={"name": ["in", ccp_names or [""]], "status": "In Process"},
		pluck="name",
	):
		frappe.db.set_value("Candidate Country Process", ccp_name, "status", "Arriving")
