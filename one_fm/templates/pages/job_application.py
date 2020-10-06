from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


def get_context(context):
    context.show_search = True


# @frappe.whitelist(allow_guest=True)
# def get_dummy():
#     doc = frappe.get_doc('ERF')

#     doc.title = 'Test'
#     doc.save()
#     return doc
# @frappe.whitelist(allow_guest=True)
# def get_jobs_info():
#     job_name = []
#     job_title = []
#     job_description = []

#     jobs = frappe.db.sql(
#         """ select name,job_title,description from `tabJob Opening` where status='Open' """)
#     if jobs:
#         for job in jobs:
#             job_name.append(job[0])
#             job_title.append(job[1])
#             job_description.append(job[2])
#         return job_name, job_title, job_description
#     else:
#         return None
