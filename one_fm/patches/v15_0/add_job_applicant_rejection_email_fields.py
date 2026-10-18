from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.job_applicant import get_job_applicant_custom_fields

NEW_FIELDS = ("one_fm_rejected_on", "one_fm_rejection_email_sent")


def execute():
	"""Add the two rejection-email fields to Job Applicant.

	Deliberately no backfill: a NULL ``one_fm_rejected_on`` is what keeps the historic
	Rejected applicants out of the 48-hour rejection email job.
	"""
	fields = [
		field
		for field in get_job_applicant_custom_fields()["Job Applicant"]
		if field["fieldname"] in NEW_FIELDS
	]
	create_custom_fields({"Job Applicant": fields})
