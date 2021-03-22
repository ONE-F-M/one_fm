# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe, json
from frappe.utils import get_url, fmt_money, month_diff
from frappe.model.mapper import get_mapped_doc
from frappe import _

@frappe.whitelist()
def get_performance_profile_resource():
    file_path = frappe.db.get_value('Hiring Settings', None, 'performance_profile_resource')
    if file_path:
        return get_url(file_path)

@frappe.whitelist()
def get_performance_profile_guid():
    file_path = frappe.db.get_value('Hiring Settings', None, 'performance_profile_guid')
    if file_path:
        return get_url(file_path)

def validate_job_offer(doc, method):
    if doc.one_fm_erf and not doc.one_fm_salary_structure:
        erf_salary_structure = frappe.db.get_value('ERF', doc.one_fm_erf, 'salary_structure')
        if erf_salary_structure:
            doc.one_fm_salary_structure = erf_salary_structure
    if doc.one_fm_salary_structure:
        salary_structure = frappe.get_doc('Salary Structure', doc.one_fm_salary_structure)
        total_amount = 0
        doc.set('one_fm_salary_details', [])
        for salary in salary_structure.earnings:
            total_amount += salary.amount
            salary_details = doc.append('one_fm_salary_details')
            salary_details.salary_component = salary.salary_component
            salary_details.amount = salary.amount
        doc.one_fm_job_offer_total_salary = total_amount
    elif doc.one_fm_salary_details:
        total_amount = 0
        for salary in doc.one_fm_salary_details:
            total_amount += salary.amount if salary.amount else 0
        doc.one_fm_job_offer_total_salary = total_amount
    if frappe.db.exists('Letter Head', 'ONE FM - Job Offer') and not doc.letter_head:
        doc.letter_head = 'ONE FM - Job Offer'

def after_insert_job_applicant(doc, method):
    website_user_for_job_applicant(doc.email_id, doc.one_fm_first_name, doc.one_fm_last_name, doc.one_fm_applicant_password)
    notify_recruiter_and_requester_from_job_applicant(doc, method)

def website_user_for_job_applicant(email_id, first_name, last_name='', applicant_password=False):
    if not frappe.db.exists ("User", email_id):
        from frappe.utils import random_string
        user = frappe.get_doc({
            "doctype": "User",
            "first_name": first_name,
            "last_name": last_name,
            "email": email_id,
            "user_type": "Website User",
            "send_welcome_email": False
        })
        user.flags.ignore_permissions=True
        # user.reset_password_key=random_string(32)
        user.add_roles("Job Applicant")
        if applicant_password:
            from frappe.utils.password import update_password
            update_password(user=user.name, pwd=applicant_password)
        return user

def notify_recruiter_and_requester_from_job_applicant(doc, method):
    if doc.one_fm_erf:
        recipients = []
        erf_details = frappe.db.get_values('ERF', filters={'name': doc.one_fm_erf},
        fieldname=["erf_requested_by", "recruiter_assigned", "secondary_recruiter_assigned"], as_dict=True)
        if erf_details and len(erf_details) == 1:
            if erf_details[0].erf_requested_by and erf_details[0].erf_requested_by != 'Administrator':
                recipients.append(erf_details[0].erf_requested_by)
            if erf_details[0].recruiter_assigned:
                recipients.append(erf_details[0].recruiter_assigned)
            if erf_details[0].secondary_recruiter_assigned:
                recipients.append(erf_details[0].secondary_recruiter_assigned)
        designation = frappe.db.get_value('Job Opening', doc.job_title, 'designation')
        page_link = get_url("/desk#Form/Job Applicant/" + doc.name)
        message = "<p>There is a Job Application created for the position {2} <a href='{0}'>{1}</a></p>".format(page_link, doc.name, designation)

        if recipients:
            frappe.sendmail(
                recipients= recipients,
                subject='Job Application created for {0}'.format(designation),
                message=message,
                reference_doctype=doc.doctype,
                reference_name=doc.name
            )

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
    def set_missing_values(source, target):
        set_map_job_applicant_details(target, source.name, source)

    doc = get_mapped_doc("Job Applicant", source_name, {
        "Job Applicant": {
            "doctype": "Employee",
            "field_map": {
                "applicant_name": "employee_name",
            }
        }
    }, target_doc, set_missing_values)
    return doc

@frappe.whitelist()
def make_employee_from_job_offer(source_name, target_doc=None):
    def set_missing_values(source, target):
        if source.one_fm_salary_structure:
            target.one_fm_salary_type = frappe.db.get_value('Salary Structure', source.one_fm_salary_structure, 'payroll_frequency')
            salary_structure = frappe.get_doc('Salary Structure', source.one_fm_salary_structure)
            if salary_structure.earnings:
                for earning in salary_structure.earnings:
                    if earning.salary_component == 'Basic':
                        target.one_fm_basic_salary = earning.amount
            target.salary_mode = salary_structure.mode_of_payment
        set_map_job_applicant_details(target, source.job_applicant)
    doc = get_mapped_doc("Job Offer", source_name, {
        "Job Offer": {
            "doctype": "Employee",
            "field_map": {
                "applicant_name": "employee_name",
                "name": "job_offer",
                "one_fm_salary_structure": "job_offer_salary_structure"
            }
        }
    }, target_doc, set_missing_values)
    return doc

def set_map_job_applicant_details(target, job_applicant_id, job_applicant=False):
    if not job_applicant:
        job_applicant = frappe.get_doc('Job Applicant', job_applicant_id)
        target.nationality_no = job_applicant.nationality_no
        target.nationality_subject = job_applicant.nationality_subject
        target.date_of_naturalization = job_applicant.date_of_naturalization

    fields_map = {'personal_email': 'email_id', 'middle_name': 'one_fm_second_name',
        'one_fm_civil_id': 'one_fm_cid_number', 'cell_number': 'one_fm_contact_number',
        'date_of_issue': 'one_fm_passport_issued', 'valid_upto': 'one_fm_passport_expire',
        'place_of_issue': 'one_fm_passport_holder_of',
        'one_fm__highest_educational_qualification': 'one_fm_educational_qualification'}
    for field in fields_map:
        target.set(field, job_applicant.get(fields_map[field]))

    one_fm_prefix_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'passport_number', 'marital_status']
    for field in one_fm_prefix_fields:
        target.set(field, job_applicant.get('one_fm_'+field))

    target.department, target.designation, target.grade, target.project = frappe.db.get_value("ERF", \
		job_applicant.one_fm_erf, ["department", "designation", "grade", "project"])

    target.status = 'Active'
    if target.department:
        dept_code = frappe.db.get_value('Department', target.department, 'department_code')
        target.department_code = dept_code if dept_code else ''

    external_work_history = target.append('external_work_history')
    external_work_history.company_name = job_applicant.one_fm_current_employer
    external_work_history.designation = job_applicant.one_fm_current_job_title
    external_work_history.salary = job_applicant.one_fm_current_salary
    exp_in_month = month_diff(job_applicant.one_fm_employment_end_date, job_applicant.one_fm_employment_start_date)
    if exp_in_month:
        external_work_history.total_experience = exp_in_month / 12

def employee_after_insert(doc, method):
    create_salary_structure_assignment(doc, method)
    update_erf_close_with(doc)

def update_erf_close_with(doc):
    if doc.one_fm_erf:
        erf = frappe.get_doc('ERF', doc.one_fm_erf)
        employees = erf.append('erf_employee')
        employees.employee = doc.name
        erf.save(ignore_permissions=True)

@frappe.whitelist()
def create_salary_structure_assignment(doc, method):
    if doc.job_offer_salary_structure:
        assignment = frappe.new_doc("Salary Structure Assignment")
        assignment.employee = doc.name
        assignment.salary_structure = doc.job_offer_salary_structure
        assignment.company = doc.company
        assignment.from_date = doc.date_of_joining
        assignment.save(ignore_permissions = True)

@frappe.whitelist()
def update_job_offer_from_applicant(jo, status):
    job_offer = frappe.get_doc('Job Offer', jo)
    job_offer.status = status
    job_offer.save()

@frappe.whitelist()
def update_applicant_status(names, status_field, status, reason_for_rejection=False):
    names = json.loads(names)
    for name in names:
        job_applicant = frappe.get_doc("Job Applicant", name)
        job_applicant.set(status_field, status)
        job_applicant.one_fm_reason_for_rejection = reason_for_rejection if reason_for_rejection else ''
        job_applicant.save()

@frappe.whitelist()
def add_remove_salary_advance(names, dialog):
    names = json.loads(names)
    job_offer_list = []
    for name in names:
        job_offer = frappe.get_doc("Job Offer", name)
        if not job_offer.one_fm_notified_finance_department:
            args = json.loads(dialog)
            job_offer.one_fm_provide_salary_advance = args['one_fm_provide_salary_advance']
            if job_offer.one_fm_provide_salary_advance:
                job_offer.one_fm_salary_advance_amount = args['one_fm_salary_advance_amount']
            job_offer.save(ignore_permissions=True)
            if args['notify_finance_department']:
                job_offer_list.append(job_offer)

    if job_offer_list and len(job_offer_list) > 0:
        notify_finance_job_offer_salary_advance(job_offer_list=job_offer_list)

# Notify Daily
@frappe.whitelist()
def notify_finance_job_offer_salary_advance(job_offer_id=None, job_offer_list=None):
    if not job_offer_list:
        if job_offer_id:
            filters = {'name': job_offer_id}
        else:
            filters = {
                'one_fm_provide_salary_advance': 1, 'one_fm_salary_advance_paid': 0,
                'one_fm_salary_advance_amount': ['>', 0], 'one_fm_notified_finance_department': 0
            }
        job_offer_list = frappe.db.get_list('Job Offer', filters, ['name', 'one_fm_salary_advance_amount'])
    recipient = frappe.db.get_value('Hiring Settings', None, 'notify_finance_department_for_job_offer_salary_advance')

    if recipient and job_offer_list and len(job_offer_list)>0:
        message = "<p>Job Offer listed below needs Advance Salary</p><ol>"
        for job_offer in job_offer_list:
            doc = frappe.get_doc('Job Offer', job_offer.name)
            frappe.db.set_value('Job Offer', job_offer.name, 'one_fm_notified_finance_department', True)
            page_link = get_url("/desk#Form/Job Offer/"+job_offer.name)
            message += "<li><a href='{0}'>{1}</a>: {2}</li>".format(page_link, job_offer.name,
                fmt_money(abs(job_offer.one_fm_salary_advance_amount), 3, 'KWD'))
        message += "<ol>"
        frappe.sendmail(
            recipients=[recipient],
            subject=_('Advance Salary for Job Offer'),
            message=message,
            header=['Payment Request for Job Offer Advance Salary', 'yellow'],
        )

@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
	return frappe.get_all("Onboard Employee Activity",
		fields=["action", "role", "user", "required_for_employee_creation", "description"],
		filters={"parent": parent, "parenttype": parenttype},
		order_by= "idx")
