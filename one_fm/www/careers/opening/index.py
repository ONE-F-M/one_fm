import frappe
from ..utils import remove_html_tags

def get_context(context):
    no_cache = 1
    job_id = frappe.form_dict.job_id
    context.lang = frappe.form_dict.lang

    opening = {}

    job_opening = frappe.get_doc("Job Opening", {'name': job_id})

    if job_opening:
        opening.update({'name': job_opening.name})
        
        opening.update({'job_title': job_opening.job_title})
        opening.update({'description': job_opening.description if job_opening.description else ""})
    
        opening.update({'job_title_ar': job_opening.job_title_in_arabic})
        opening.update({'description_ar': job_opening.description_in_arabic if job_opening.description_in_arabic else ""})
       
        opening.update({'designation': job_opening.designation})
        
    
    context.opening = opening
