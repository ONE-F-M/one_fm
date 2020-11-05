from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


def get_context(context):
    context.show_search = True


@frappe.whitelist(allow_guest=True)
def get_dummy():
    # doc = frappe.get_doc('ERF', fields=[*])
    doc = frappe.db.get_all('ERF', fields=['*'])
    # doc.title = 'Test'
    # doc.save()
    return doc
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

@frappe.whitelist(allow_guest=True)
def easy_apply(applicant_name, applicant_email, applicant_mobile, cover_letter, designation):
    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None

    subject = """<b>Subject:</b> Application for {0}<br>""".format(designation)
    message_details = """
        <b>Name:</b> {0}<br>
        <b>Email:</b> {1}<br>
        <b>Mobile:</b> {2}<br>
        <hr stle='width:50%;'>
        <b>Message:</b><br><br>
        {3}
    """.format(applicant_name, applicant_email, applicant_mobile, cover_letter)

    try:
        # Notify the HR User
        frappe.sendmail(sender=sender, recipients= 'j.poil@armor-services.com',
            content=message_details, subject=contact_subject)

        # Email back to the Applicant
        applied_subject =  "Thanks for applying for {0}".format(designation)
        applied_msg =  "<b>We have received your email and our HR team will be responding to you soon.</b>"
        frappe.sendmail(sender=sender, recipients= applicant_email,
            content=applied_msg, subject=applied_subject)
        return 1
    except:
        return 0

@frappe.whitelist(allow_guest=True)
def create_job_applicant(job_opening, job_applicant_fields, languages=None, skills=None, files=None):
    job_applicant = frappe.db.exists("Job Applicant", {"job_title": job_opening, "email_id": email_id})
    if job_applicant:
        return job_applicant
    else:
        job_applicant = frappe.new_doc('Job Applicant')
        job_applicant.job_title = job_opening
        set_job_applicant_fields(job_applicant, job_applicant_fields)
        if languages:
            set_languages(job_applicant, languages)
        if skills:
            set_skills(job_applicant, skills)
        job_applicant.insert(ignore_permissions=True)
        return 1, job_applicant.name

def set_job_applicant_fields(doc, job_applicant_fields):
    for field in job_applicant_fields:
        doc.set(field, job_applicant_fields.field)

def set_skills(doc, skills):
    for designation_skill in skills:
        skill = doc.append('one_fm_designation_skill')
        skill.skill = designation_skill.skill
        skill.proficiency = designation_skill.proficiency

def set_languages(doc, languages):
    for language in languages:
        lang = doc.append('one_fm_languages')
        lang.language = language.language
        lang.language_name = language.language_name
        lang.speak = language.speak
        lang.read = language.read
        lang.write = language.write
