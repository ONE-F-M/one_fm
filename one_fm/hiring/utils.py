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
        fields_map = {'personal_email': 'email_id', 'middle_name': 'one_fm_second_name',
            'one_fm_civil_id': 'one_fm_cid_number', 'cell_number': 'one_fm_contact_number',
            'date_of_issue': 'one_fm_passport_issued', 'valid_upto': 'one_fm_passport_expire',
            'place_of_issue': 'one_fm_passport_holder_of',
            'one_fm__highest_educational_qualification': 'one_fm_educational_qualification'}
        for field in fields_map:
            target.set(field, source.get(fields_map[field]))

        one_fm_prefix_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'passport_number', 'marital_status']
        for field in one_fm_prefix_fields:
            target.set(field, source.get('one_fm_'+field))

        target.department, target.designation, target.grade, target.project = frappe.db.get_value("ERF", \
			source.one_fm_erf, ["department", "designation", "grade", "project"])

        target.status = 'Active'
        if target.department:
            dept_code = frappe.db.get_value('Department', target.department, 'department_code')
            target.department_code = dept_code if dept_code else ''

        external_work_history = target.append('external_work_history')
        external_work_history.company_name = source.one_fm_current_employer
        external_work_history.designation = source.one_fm_current_job_title
        external_work_history.salary = source.one_fm_current_salary
        exp_in_month = month_diff(source.one_fm_employment_end_date, source.one_fm_employment_start_date)
        if exp_in_month:
            external_work_history.total_experience = exp_in_month / 12

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
