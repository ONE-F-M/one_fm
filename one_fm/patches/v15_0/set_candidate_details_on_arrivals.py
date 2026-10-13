"""Fill the candidate's details on existing overseas arrivals: department from the CCP, the rest from the Job Applicant."""

import frappe

from one_fm.one_fm.doctype.arrival_and_deployment.arrival_and_deployment import (
	get_job_applicant_designation,
)

JOB_APPLICANT_FIELDS = {
	"gender": "one_fm_gender",
	"nationality": "one_fm_nationality",
	"date_of_birth": "one_fm_date_of_birth",
}


def execute():
	arrivals = frappe.get_all(
		"Arrival and Deployment",
		filters={"candidate_country_process": ["is", "set"], "job_applicant": ["is", "not set"]},
		fields=["name", "candidate_country_process"],
	)
	for arrival in arrivals:
		ccp = frappe.db.get_value(
			"Candidate Country Process",
			arrival.candidate_country_process,
			["job_applicant", "department"],
			as_dict=True,
		)
		if not (ccp and ccp.job_applicant):
			continue
		job_applicant, department = ccp.job_applicant, ccp.department

		values = frappe.db.get_value(
			"Job Applicant", job_applicant, list(JOB_APPLICANT_FIELDS.values()), as_dict=True
		)
		if not values:
			continue
		details = {field: values[source] for field, source in JOB_APPLICANT_FIELDS.items()}
		frappe.db.set_value(
			"Arrival and Deployment",
			arrival.name,
			{
				"job_applicant": job_applicant,
				"department": department,
				"designation": get_job_applicant_designation(job_applicant),
				**details,
			},
			update_modified=False,
		)
