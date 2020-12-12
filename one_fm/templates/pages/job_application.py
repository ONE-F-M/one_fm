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

@frappe.whitelist(allow_guest=True)
def easy_apply(first_name, second_name, third_name, last_name, nationality, civil_id, applicant_email, applicant_mobile,
    cover_letter, job_opening, resume=None):
    sender = frappe.get_value("Email Account", filters={"default_outgoing": 1}, fieldname="email_id") or None
    applicant_name = first_name
    applicant_name += (" "+second_name) if second_name else ""
    applicant_name += (" "+third_name) if third_name else ""
    applicant_name += " "+last_name
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
    create_job_applicant_for_easy_apply(applicant_name, first_name, second_name, third_name, last_name, nationality,
        civil_id, applicant_email, applicant_mobile, cover_letter, job_opening)
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

def create_job_applicant_for_easy_apply(applicant_name, first_name, second_name, third_name, last_name, nationality,
        civil_id, applicant_email, applicant_mobile, cover_letter, job_opening, files=None):
    job_applicant = frappe.db.exists(
        "Job Applicant", {"job_title": job_opening, "email_id": applicant_email})
    if job_applicant:
        return job_applicant
    else:
        job_applicant = frappe.new_doc('Job Applicant')
        job_applicant.job_title = job_opening
        job_applicant.one_fm_erf = frappe.db.get_value('Job Opening', job_opening, "one_fm_erf")
        job_applicant.applicant_name = applicant_name
        job_applicant.one_fm_email_id = applicant_email
        job_applicant.one_fm_first_name = first_name
        job_applicant.one_fm_second_name = second_name
        job_applicant.one_fm_third_name = third_name
        job_applicant.one_fm_last_name = last_name
        job_applicant.one_fm_nationality = nationality
        job_applicant.one_fm_cid_number = civil_id
        job_applicant.one_fm_contact_number = applicant_mobile
        job_applicant.one_fm_is_easy_apply = True
        job_applicant.insert(ignore_permissions=True)

@frappe.whitelist(allow_guest=True)
def create_job_applicant(job_opening, email_id, job_applicant_fields, languages=None, skills=None, files=None):
    job_applicant = frappe.db.exists(
        "Job Applicant", {"job_title": job_opening, "email_id": email_id})
    if job_applicant:
        return job_applicant
    else:
        job_applicant = frappe.new_doc('Job Applicant')
        job_applicant.job_title = job_opening

        fields_json = json.loads(job_applicant_fields)
        fields = frappe._dict(fields_json)

        set_job_applicant_fields(job_applicant, fields)

        if languages:
            languages_json = json.loads(languages)
            set_languages(job_applicant, languages_json)
        if skills:
            skills_json = json.loads(skills)
            set_skills(job_applicant, skills_json)
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
    name_fields = ['one_fm_second_name', 'one_fm_third_name', 'one_fm_last_name']
    applicant_name = doc.one_fm_first_name if doc.one_fm_first_name else ''
    for name_field in name_fields:
        if doc.get(name_field):
            applicant_name += ' '+doc.get(name_field)
    doc.applicant_name = applicant_name

def set_skills(doc, skills):
    for designation_skill in skills:
        skill = doc.append('one_fm_designation_skill')
        skill.skill = designation_skill['skill']
        skill.proficiency = designation_skill['proficiency']

def set_languages(doc, languages):
    for language in languages:
        lang = doc.append('one_fm_languages')
        lang.language = language['language']
        lang.language_name = language['language_name']
        lang.speak = language['speak']
        lang.read = language['read']
        lang.write = language['write']

@frappe.whitelist(allow_guest=True)
def get_job_details(job):
    erf = False
    erf_id = frappe.db.get_value('Job Opening', job, 'one_fm_erf')
    if erf_id:
        erf = frappe.get_doc('ERF', erf_id)
    return erf

@frappe.whitelist(allow_guest=True)
def get_required_documents(job, visa_type=None):
    filters = {}
    source_of_hire = frappe.db.get_value('Job Opening', job, 'one_fm_source_of_hire')
    if source_of_hire == 'Local and Overseas' and visa_type:
        source_of_hire = 'Local'
    filters['visa_type'] = visa_type if visa_type else ''
    filters['source_of_hire'] = source_of_hire

    from one_fm.one_fm.doctype.recruitment_document_checklist.recruitment_document_checklist import get_recruitment_document_checklist
    return get_recruitment_document_checklist(filters)
