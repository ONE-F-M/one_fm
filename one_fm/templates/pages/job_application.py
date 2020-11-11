from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url


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
def easy_apply(applicant_name, applicant_email, applicant_mobile, cover_letter, job_opening, resume=None):
    sender = frappe.get_value("Email Account", filters={"default_outgoing": 1}, fieldname="email_id") or None

    job = frappe.get_doc('Job Opening', job_opening)
    erf_link = get_url("/desk#Form/ERF/" + job.one_fm_erf)
    job_link = get_url("/desk#Form/Job Opening/" + job.name)
    subject = """Application for {0}""".format(job.designation)
    message_details = """
        <b>Name:</b> {0}<br>
        <b>Email:</b> {1}<br>
        <b>Mobile:</b> {2}<br>
        <hr stle='width:50%;'>
        <b>Message:</b><br><br>
        {3}
        <br><br><br><b>Reference:</b> ERF <a href='{4}'>{5}</a> and Job Opening <a href='{6}'>{7}</a>
    """.format(applicant_name, applicant_email, applicant_mobile, cover_letter, erf_link, job.one_fm_erf, job_link, job.name)

    try:
        # Notify the HR User
        hr_user_to_get_notified = frappe.db.get_single_value('Hiring Settings', 'easy_apply_to') or 'hr@one-fm.com'
        frappe.sendmail(sender=sender, recipients=[hr_user_to_get_notified], content=message_details, subject=subject)

        # Email back to the Applicant
        applied_subject = "Thanks for applying for {0}".format(job.designation)
        applied_msg = "<b>We have received your email and our HR team will be responding to you soon.</b>"
        frappe.sendmail(sender=sender, recipients=[applicant_email], content=applied_msg, subject=applied_subject)
        return 1
    except:
        return 0


@frappe.whitelist(allow_guest=True)
def create_job_applicant(job_opening, email_id, job_applicant_fields, languages=None, skills=None, files=None):
    job_applicant = frappe.db.exists(
        "Job Applicant", {"job_title": job_opening, "email_id": email_id})
    if job_applicant:
        return job_applicant
    else:
        job_applicant = frappe.new_doc('Job Applicant')
        job_applicant.one_fm_erf = job_opening
        job_applicant.applicant_name = "DDDDD"
        job_applicant.job_title = frappe.db.get_value('Job Opening', {'one_fm_erf': job_opening})

        fields_json = json.loads(job_applicant_fields)
        fields = frappe._dict(fields_json)

        set_job_applicant_fields(job_applicant, fields)
        job_applicant.one_fm_passport_type = 'Normal'
        job_applicant.one_fm_rotation_shift = 'No, I Cant Work in Rotation Shift'
        job_applicant.one_fm_night_shift = 'No, I Cant Work in Night Shift'
        # if languages:
        #     languages_json = json.loads(languages)
        #     languages_obj = frappe._dict(languages_json)
        #     set_languages(job_applicant, languages_obj)
        # if skills:
        #     skills_json = json.loads(skills)
        #     skills_obj = frappe._dict(skills_json)
        #     set_skills(job_applicant, skills)
        # if files:
        #     files_json = json.loads(files)
        #     files_obj = frappe._dict(files_json)
        #     set_files_to_job_applicant(job_applicant, files_obj)
        job_applicant.insert(ignore_permissions=True)
        return 1

def set_files_to_job_applicant(doc, files):
    for file in files:
        documents_required = doc.append('one_fm_documents_required')
        documents_required.document_required = file.document_required
        attach_file_to_application(file.filedata, doc.name)
        # documents_required.attach = file.url

@frappe.whitelist()
def attach_file_to_application(filedata, job_applicant_id):
    from frappe.utils.file_manager import save_file
    if filedata:
        fd_json = json.loads(filedata)
        fd_list = list(fd_json["files_data"])
        for fd in fd_list:
            filedoc = save_file(fd["filename"], fd["dataurl"], "Job Applicant", job_applicant_id, decode=True, is_private=0)

def set_job_applicant_fields(doc, fields):
    for field in fields:
        doc.set(field, fields[field])

def set_skills(doc, skills):
    for designation_skill in skills:
        skill = doc.append('one_fm_designation_skill')
        skill.skill = designation_skill[skill]
        skill.proficiency = designation_skill[proficiency]


def set_languages(doc, languages):
    for language in languages:
        lang = doc.append('one_fm_languages')
        lang.language = language[language]
        lang.language_name = language[language_name]
        lang.speak = language[speak]
        lang.read = language[read]
        lang.write = language[write]
