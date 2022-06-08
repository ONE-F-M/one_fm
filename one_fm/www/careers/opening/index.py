import frappe
from ..utils import remove_html_tags

def get_context(context):
    no_cache = 1
    job_id = frappe.form_dict.job_id

    opening = {}

    job_opening = frappe.get_doc("Job Opening", {'name': job_id})

    if job_opening:
        opening.update({'name': job_opening.name})
        opening.update({'designation': job_opening.designation})
        opening.update({'description': job_opening.description if job_opening.description else ""})

    context.opening = opening
