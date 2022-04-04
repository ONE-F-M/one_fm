from datetime import datetime
import frappe
from frappe.utils import getdate, today

def uncheck_publish_job_opening_on_valid_till():
    """
        The method is used to fetch all the Job Oppening valid for yesterday and published
        then update to false for publish
    """
    job_opening_list = frappe.get_list('Job Opening',
        filters={'publish': True, 'one_fm_job_post_valid_till': ['<', getdate(today())]},
        fields=['name', 'one_fm_job_post_valid_till'])
    for job_opening in job_opening_list:
        if job_opening.one_fm_job_post_valid_till:
            frappe.db.set_value('Job Opening', job_opening.name, 'publish', False)
