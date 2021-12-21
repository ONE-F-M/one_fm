from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url

def get_context(context):
    context.parents = [{'route': 'jobs', 'title': _('All Jobs') }]
    context.title = _("Application")
    # Get job opening id from url to the context // frappe.form_dict.<args in url>
    context.job_opening = frappe.get_doc('Job Opening', frappe.form_dict.job_title)
    # Get Country List to the context to show in the portal
    context.country_list = frappe.get_all('Country', fields=['name'])

@frappe.whitelist(allow_guest=True)
def easy_apply(first_name, second_name, third_name, last_name, nationality, civil_id, applicant_email, applicant_mobile,
    cover_letter, job_opening, first_name_arabic, last_name_arabic, resume=None):
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
        civil_id, applicant_email, applicant_mobile, cover_letter, job_opening, first_name_arabic, last_name_arabic)
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
def create_job_applicant_from_job_portal(applicant_name, country, applicant_email, applicant_mobile, job_opening, files):
    '''
        Method to create Job Applicant from Portal
        args:
            applicant_name: Name of the Applicant
            country: Country of the Applicant
            applicant_email: Applicant Email ID
            applicant_mobile: Applicant Mobile Number
            job_opening: Job Opening ID
            files: The CV attached
        Return True if Job Applicant created Succesfully
        Return job_applicant if Job Applicant already exists for the job opening and applicant email_id combination
    '''

    # Return job_applicant if Job Applicant already exists for the job opening and applicant email_id combination
    job_applicant = frappe.db.exists("Job Applicant", {"job_title": job_opening, "email_id": applicant_email})
    if job_applicant:
        return job_applicant
    else:
        # Get Nationality from country given by the applicant
        nationality = frappe.db.exists('Nationality', {'country': country})
        # Create Job Applicant
        job_applicant = frappe.new_doc('Job Applicant')
        job_applicant.job_title = job_opening
        job_applicant.applicant_name = applicant_name
        job_applicant.one_fm_nationality = nationality if nationality else ''
        job_applicant.one_fm_email_id = applicant_email
        job_applicant.one_fm_contact_number = applicant_mobile
        job_applicant.one_fm_erf = frappe.db.get_value('Job Opening', job_opening, "one_fm_erf")
        job_applicant.one_fm_is_easy_apply = True

        job_applicant.one_fm_first_name = applicant_name
        job_applicant.one_fm_first_name_in_arabic = applicant_name
        job_applicant.one_fm_last_name = applicant_name
        job_applicant.one_fm_last_name_in_arabic = applicant_name

        job_applicant.save(ignore_permissions=True)

        # If files exisit, attach the file to Job Applicant created
        if files:
            files_json = json.loads(files)
            files_obj = frappe._dict(files_json)
            for file in files_obj:
                # Attach the file to Job Applicant created
                attach_file_to_job_applicant(files_obj[file]['files_data'], job_applicant)
            job_applicant.save(ignore_permissions=True)
        return True

@frappe.whitelist()
def attach_file_to_job_applicant(filedata, job_applicant):
    '''
        Method to save file to db, attach file to job applicant and set resume_attachment field in Job Applicant
        args:
            filedata: filedata
            job_applicant: Object of Job Applicant
    '''
    from frappe.utils.file_manager import save_file
    if filedata:
        for fd in filedata:
            # Save file and attach to Job Applicant
            filedoc = save_file(fd["filename"], fd["dataurl"], "Job Applicant", job_applicant.name, decode=True, is_private=0)
            # Set resume_attachment as url of the file stored
            job_applicant.resume_attachment = filedoc.file_url

def create_job_applicant_for_easy_apply(applicant_name, first_name, second_name, third_name, last_name, nationality,
        civil_id, applicant_email, applicant_mobile, cover_letter, job_opening, first_name_arabic, last_name_arabic, files=None):
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
        job_applicant.one_fm_first_name_in_arabic = first_name_arabic
        job_applicant.one_fm_second_name = second_name
        job_applicant.one_fm_third_name = third_name
        job_applicant.one_fm_last_name = last_name
        job_applicant.one_fm_last_name_in_arabic = last_name_arabic
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
        job_applicant.save(ignore_permissions=True)
        if files:
            files_json = json.loads(files)
            files_obj = frappe._dict(files_json)
            for file in files_obj:
                attach_file_to_application(files_obj[file]['files_data'], job_applicant, file)
            job_applicant.save(ignore_permissions=True)
        return 1

@frappe.whitelist()
def attach_file_to_application(filedata, job_applicant, document_required):
    from frappe.utils.file_manager import save_file
    if filedata:
        for fd in filedata:
            filedoc = save_file(fd["filename"], fd["dataurl"], "Job Applicant", job_applicant.name, decode=True, is_private=0)
            for documents_required in job_applicant.one_fm_documents_required:
                if documents_required.document_required == document_required.replace("-", " "):
                    documents_required.attach = filedoc.file_url

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
        skill.one_fm_proficiency = designation_skill['proficiency']

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
def get_country_from_nationality(nationality):
    return frappe.db.get_value('Nationality', nationality, 'country')

@frappe.whitelist(allow_guest=True)
def get_master_details():
    gender = frappe.db.get_list('Gender')
    nationality = frappe.db.get_list('Nationality')
    country = frappe.db.get_list('Country')
    visaType = frappe.db.get_list('Visa Type')
    return {'gender': gender, 'nationality': nationality, 'passportHolderOf': country,
        'country_of_employment': country, 'visaType': visaType}

@frappe.whitelist(allow_guest=True)
def get_required_documents(job=None, visa_type=None, nationality=None, valid_kuwait_visa=None):
    filters = {}
    source_of_hire = ''

    if job:
        source_of_hire = frappe.db.get_value('Job Opening', job, 'one_fm_source_of_hire')
        if source_of_hire == 'Local and Overseas' and visa_type:
            source_of_hire = 'Local'

    if nationality == 'Kuwaiti':
        source_of_hire = 'Kuwaiti'
    elif valid_kuwait_visa:
        source_of_hire = 'Local'
    else:
        source_of_hire = 'Overseas'

    if valid_kuwait_visa and visa_type:
        filters['visa_type'] = visa_type
    filters['source_of_hire'] = source_of_hire

    from one_fm.one_fm.doctype.recruitment_document_checklist.recruitment_document_checklist import get_recruitment_document_checklist
    return get_recruitment_document_checklist(filters)
