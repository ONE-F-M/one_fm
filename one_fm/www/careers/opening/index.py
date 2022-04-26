import frappe
from ..utils import remove_html_tags

def get_context(context):

    job_id = frappe.form_dict.job_id

    opening = {}

    if job_id:
        designation, description = frappe.db.get_value("Job Opening", {'name': job_id}, ["designation", "description"])
        opening.update({'name': job_id})
        opening.update({'designation': designation})
        opening.update({'description': remove_html_tags(description) if description else ""})

    context.opening = opening