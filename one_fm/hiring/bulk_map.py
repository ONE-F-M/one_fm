"""Whether the Job Applicant Lifecycle - Bulk process map handles an applicant's hiring.

The map creates and sends the Job Offer, emails it, hands the candidate to onboarding and
sends the rejection email, so the code that did those steps aside for the applicants it
handles. Applicants it does not handle keep the code.
"""

import frappe

BULK_MAP_PROCESS_PREFIX = "job_applicant_bulk"
RUNNING_STATUSES = ("Active", "Queued")


def handled_by_bulk_map(job_applicant: str | None) -> bool:
	"""True when a Bulk map is running this applicant, or has finished a Bulk Recruitment applicant."""
	if not job_applicant or not frappe.db.exists("DocType", "BPMN Process Instance"):
		return False
	models = frappe.get_all(
		"BPMN Process Model",
		filters={"process_id": ["like", BULK_MAP_PROCESS_PREFIX + "%"]},
		pluck="name",
	)
	if not models:
		return False
	statuses = frappe.get_all(
		"BPMN Process Instance",
		filters={
			"context_doctype": "Job Applicant",
			"context_docname": job_applicant,
			"process_model": ["in", models],
		},
		pluck="status",
	)
	if any(status in RUNNING_STATUSES for status in statuses):
		return True
	# The map also finishes at once for applicants outside Bulk Recruitment, and those keep the code.
	return "Completed" in statuses and (
		frappe.db.get_value("Job Applicant", job_applicant, "one_fm_hiring_method") == "Bulk Recruitment"
	)
