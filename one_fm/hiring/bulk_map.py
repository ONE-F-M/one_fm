"""Whether the Job Applicant Lifecycle - Bulk process map handles an applicant's hiring.

The map creates and sends the Job Offer, emails it, hands the candidate to onboarding and
sends the rejection email, so the code that did those steps aside while the map runs an
applicant. Applicants it does not run keep the code, including a re-opened applicant
whose map has already finished.
"""

import frappe

BULK_MAP_PROCESS_PREFIX = "job_applicant_bulk"
RUNNING_STATUSES = ("Active", "Queued")


def bulk_map_running(job_applicant: str | None) -> bool:
	"""True when a Job Applicant Lifecycle - Bulk map is running this applicant."""
	return any(status in RUNNING_STATUSES for status in _bulk_map_statuses(job_applicant))


def bulk_map_handled(job_applicant: str | None) -> bool:
	"""True when a Bulk map is running this applicant, or finished it and the applicant is Bulk Recruitment."""
	statuses = _bulk_map_statuses(job_applicant)
	if any(status in RUNNING_STATUSES for status in statuses):
		return True
	# The map also finishes at once for applicants outside Bulk Recruitment, and those keep the code.
	return "Completed" in statuses and (
		frappe.db.get_value("Job Applicant", job_applicant, "one_fm_hiring_method") == "Bulk Recruitment"
	)


def _bulk_map_statuses(job_applicant: str | None) -> list[str]:
	if not job_applicant or not frappe.db.exists("DocType", "BPMN Process Instance"):
		return []
	models = frappe.get_all(
		"BPMN Process Model",
		filters={"process_id": ["like", BULK_MAP_PROCESS_PREFIX + "%"]},
		pluck="name",
	)
	if not models:
		return []
	return frappe.get_all(
		"BPMN Process Instance",
		filters={
			"context_doctype": "Job Applicant",
			"context_docname": job_applicant,
			"process_model": ["in", models],
		},
		pluck="status",
	)
