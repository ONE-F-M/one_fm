"""Draft Visa Requests a Candidate Country Process created without a Job Applicant get it, and the applicant details it fetches."""

import frappe


def execute():
	fetched = frappe.get_meta("Visa Request").get_fields_to_fetch("job_applicant")
	for visa_request in frappe.get_all(
		"Visa Request",
		filters={
			"candidate_country_process": ["is", "set"],
			"job_applicant": ["is", "not set"],
			"workflow_state": ["in", ["Draft", None]],
		},
		fields=["name", "candidate_country_process"] + [df.fieldname for df in fetched],
	):
		ccp = frappe.db.get_value(
			"Candidate Country Process",
			visa_request.candidate_country_process,
			["job_offer", "job_applicant"],
			as_dict=True,
		)
		if not ccp or not ccp.job_applicant:
			continue

		applicant = frappe.db.get_value(
			"Job Applicant",
			ccp.job_applicant,
			[df.fetch_from.split(".", 1)[1] for df in fetched],
			as_dict=True,
		)
		if not applicant:
			continue
		updates = {"job_offer": ccp.job_offer, "job_applicant": ccp.job_applicant}
		for df in fetched:
			if not visa_request.get(df.fieldname):
				updates[df.fieldname] = applicant.get(df.fetch_from.split(".", 1)[1])
		frappe.db.set_value("Visa Request", visa_request.name, updates)
