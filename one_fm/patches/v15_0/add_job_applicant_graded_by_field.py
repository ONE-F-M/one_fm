from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.job_applicant import get_job_applicant_custom_fields

NEW_FIELD = "one_fm_graded_by"


def execute():
	"""Add Graded By to Job Applicant: the recruiter the Job Applicant map assigns its tasks to."""
	fields = [
		field
		for field in get_job_applicant_custom_fields()["Job Applicant"]
		if field["fieldname"] == NEW_FIELD
	]
	create_custom_fields({"Job Applicant": fields})
