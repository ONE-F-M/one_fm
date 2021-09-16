# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, add_days, get_url
from frappe.integrations.offsite_backup_utils import get_latest_backup_file, send_email, validate_file_size, get_chunk_site
from one_fm.api.notification import create_notification_log
from frappe.utils.user import get_users_with_role

@frappe.whitelist()
def employee_grade_validate(doc, method):
    if doc.default_salary_structure:
        exists_in_list = False
        if doc.salary_structures:
            for salary_structure in doc.salary_structures:
                if salary_structure.salary_structure == doc.default_salary_structure:
                    exists_in_list = True
        if not exists_in_list:
            salary_structures = doc.append('salary_structures')
            salary_structures.salary_structure = doc.default_salary_structure

@frappe.whitelist()
def get_salary_structure_list(doctype, txt, searchfield, start, page_len, filters):
    if filters.get('employee_grade'):
        query = """
            select
                ss.salary_structure
            from
                `tabEmployee Grade` eg, `tabEmployee Grade Salary Structure` ss
            where
                ss.parent=eg.name and eg.name=%(employee_grade)s and ss.salary_structure like %(txt)s
        """
        return frappe.db.sql(query,
            {
                'employee_grade': filters.get("employee_grade"),
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )
    else:
        return frappe.db.sql("""select name from `tabSalary Structure` where name like %(txt)s""",
            {
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )

@frappe.whitelist()
def send_notification_to_grd_or_recruiter(doc, method):
    if doc.one_fm_nationality != "Kuwaiti":
        if doc.one_fm_is_transferable == 'Yes' and doc.one_fm_cid_number and doc.one_fm_passport_number:
            notify_grd_to_check_applicant_documents(doc)

        if doc.one_fm_has_issue and doc.one_fm_notify_recruiter == 0:
            notify_recruiter_after_checking(doc)

def notify_grd_to_check_applicant_documents(doc):
    """
    This method is notifying operator with applicant's cid and passport to check on PAM,
    This method runs on update and it checkes notification log list.
    """
    if not doc.one_fm_grd_operator:
        doc.one_fm_grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")

    dt = frappe.get_doc('Job Applicant',doc.name)
    if dt:
        email = [doc.one_fm_grd_operator]
        page_link = get_url("/desk#List/Job Applicant/" + dt.name)
        message = "<p>Check If Transferable.<br>Civil id:{0} - Passport Number:{1}<a href='{2}'></a>.</p>".format(dt.one_fm_cid_number,dt.one_fm_passport_number,page_link)
        subject = 'Check If Transferable.<br>Civil id:{0} - Passport Number:{1}'.format(dt.one_fm_cid_number,dt.one_fm_passport_number)
        # send_email(dt, email, message, subject)

        if not frappe.db.exists("Notification Log",{'subject':subject,'document_type':"Job Applicant"}):
        #check if the notification have been sent before.
            create_notification_log(subject, message, email, dt)

# def deleteNotification():
#     docs = frappe.db.get_list('Notification Log')
#     for doc in docs:
#         frappe.delete_doc("Notification Log", doc.name, ignore_permissions=True)
#         print("Done")

def notify_recruiter_after_checking(doc):
    """
    This method is notifying all recruiters with applicant status once,
    and changing document status into Checked By GRD.
    """
    # filtered_recruiter_users = []
    # find = False
    # users = get_users_with_role('Recruiter')
    # for user in users:
    #     filtered_recruiter_users.append(user)
    #     find = True
    #     break
    # if find and filtered_recruiter_users and len(filtered_recruiter_users) > 0:
    recruiter = frappe.db.get_value('ERF',doc.one_fm_erf,'recruiter_assigned')
    
    if recruiter:
        dt = frappe.get_doc('Job Applicant',doc.name)
        if dt:
            if dt.one_fm_has_issue == "Yes" and dt.one_fm_notify_recruiter == 0:
                email = recruiter
                page_link = get_url("/desk#List/Job Applicant/" + dt.name)
                message="<p>Tranfer for {0} has issue<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
                subject='Tranfer for {0} has issue'.format(dt.applicant_name)
                create_notification_log(subject,message,[email],dt)
                dt.db_set('one_fm_notify_recruiter', 1)
                dt.db_set('one_fm_applicant_status', "Checked By GRD")

            if dt.one_fm_has_issue == "No" and dt.one_fm_notify_recruiter == 0: 
                email = recruiter
                page_link = get_url("/desk#List/Job Applicant/" + dt.name)
                message="<p>Tranfer for {0} has no issue<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
                subject='Tranfer for {0} has no issues'.format(dt.applicant_name)
                create_notification_log(subject,message,[email],dt)
                dt.db_set('one_fm_notify_recruiter', 1)
                dt.db_set('one_fm_applicant_status', "Checked By GRD")
                notify_pam_authorized_signature(doc)#Inform Authorized signature 
                
def notify_pam_authorized_signature(doc):
    user = frappe.db.get_value('PAM Authorized Signatory Table',{'authorized_signatory_name_arabic':doc.one_fm_signatory_name},['user'])
    page_link = get_url("/desk#Form/Job Applicant/" + doc.name)
    subject = _("Attention: Your E-Signature will be used for Transfer Paper")
    message = "<p>Please note that your E-Signature will be used on Transfer Paper: <a href='{0}'></a></p>.".format(page_link)
    create_notification_log(subject, message, [user], doc)


@frappe.whitelist()
def check_mendatory_fields_for_grd_and_recruiter(doc,method):
    """
    This Method is checking the roles accessing Job Applicant document
    and setting the mendatory fields for each role based upon their selections.

    """
    roles = frappe.get_roles(frappe.session.user)
    if "GRD Operator" in roles:
        if doc.one_fm_has_issue == "No":
            validate_mendatory_fields_for_grd(doc)

        if doc.one_fm_has_issue == "Yes":
            if not doc.one_fm_type_of_issues:
                frappe.throw("Set The Type of Transfer issue before saving")
    if "Recruiter" or "Senior Recruiter" in roles:
        if doc.one_fm_is_transferable == "Yes" and doc.one_fm_have_a_valid_visa_in_kuwait == 1:
            validate_mendatory_fields_for_recruiter(doc)
        if doc.one_fm_is_transferable == "Yes" and doc.one_fm_have_a_valid_visa_in_kuwait == 0:
            frappe.throw("Visa and Residency Details are required First.")



def validate_mendatory_fields_for_grd(doc):
    """
        Check all the mendatory fields are set by grd
    """
    field_list = [{'Trade Name in Arabic':'one_fm_previous_company_trade_name_in_arabic'},{'Signatory Name':'one_fm_signatory_name'}]

    mandatory_fields = []
    for fields in field_list:
        for field in fields:
            if not doc.get(fields[field]):
                mandatory_fields.append(field)

    if len(mandatory_fields) > 0:
        message = 'Mandatory fields required in Job Applicant<br><br><ul>'
        for mandatory_field in mandatory_fields:
            message += '<li>' + mandatory_field +'</li>'
        message += '</ul>'
        frappe.throw(message)


def validate_mendatory_fields_for_recruiter(doc):
    """
        Check all the mendatory fields are set by Recruiter if Applicant wants to transfer
    """
    visa = frappe.get_doc('Visa Type',doc.one_fm_visa_type)
    if visa.has_previous_job:
        field_list = [{'CIVIL ID':'one_fm_cid_number'}, {'Date of Birth':'one_fm_date_of_birth'},
            {'Gender':'one_fm_gender'}, {'Religion':'one_fm_religion'},
            {'Nationality':'one_fm_nationality'}, {'Previous Designation':'one_fm_previous_designation'},
            {'Passport Number':'one_fm_passport_number'}, {'What is Your Highest Educational Qualification':'one_fm_educational_qualification'},
            {'Marital Status':'one_fm_marital_status'}, {'Previous Work Permit Salary':'one_fm_work_permit_salary'}]
    
    if not visa.has_previous_job:
        field_list = [{'CIVIL ID':'one_fm_cid_number'}, {'Date of Birth':'one_fm_date_of_birth'},
            {'Gender':'one_fm_gender'}, {'Religion':'one_fm_religion'},
            {'Nationality':'one_fm_nationality'},{'Passport Number':'one_fm_passport_number'}, 
            {'What is Your Highest Educational Qualification':'one_fm_educational_qualification'},
            {'Marital Status':'one_fm_marital_status'}]

    mandatory_fields = []
    for fields in field_list:
        for field in fields:
            if not doc.get(fields[field]):
                mandatory_fields.append(field)

    if len(mandatory_fields) > 0:
        message = 'Mandatory fields required in Job Applicant<br><br><ul>'
        for mandatory_field in mandatory_fields:
            message += '<li>' + mandatory_field +'</li>'
        message += '</ul>'
        frappe.throw(message)

@frappe.whitelist()
def get_signatory_name(parent,name):
    """
    This method fetching all Autorized Signatory based on the New PAM file selection in job applicant
    """
    names=[]
    names.append(' ')
    if parent and name:
        doc = frappe.get_doc('PAM Authorized Signatory List',{'pam_file_name':parent})
        job_doc = frappe.get_doc('Job Applicant',name)
        if doc:
            job_doc.one_fm_pam_authorized_signatory = doc.name
            for pas in doc.authorized_signatory:
                if pas.authorized_signatory_name_arabic:
                    names.append(pas.authorized_signatory_name_arabic)
        elif not doc:
            frappe.throw("PAM File Number Has No PAM Authorized Signatory List")
        
    return names

@frappe.whitelist()
def get_signatory_name_erf_file(parent,name):
    """
    This method fetching all Autorized Signatory based on the PAM file selection in erf
    """
    
    names=[]
    names.append(' ')
    if parent and name:
        doc = frappe.get_doc('PAM Authorized Signatory List',{'pam_file_number':parent})
        job_doc = frappe.get_doc('Job Applicant',name)
        if doc:
            job_doc.one_fm_pam_authorized_signatory = doc.name
            for pas in doc.authorized_signatory:
                if pas.authorized_signatory_name_arabic:
                    names.append(pas.authorized_signatory_name_arabic)
        elif not doc:
            frappe.throw("PAM File Number Has No PAM Authorized Signatory List")
    return names

@frappe.whitelist()
def notify_supervisor_change_file_number(name):
    job_Applicant = frappe.get_doc('Job Applicant',name)
    grd_supervisor = frappe.db.get_single_value('GRD Settings','default_grd_supervisor')
    page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
    subject = _("You Are Requested to Change/Approve New PAM File Number for Applicant with Civil ID:{0} ").format(job_Applicant.one_fm_cid_number)
    message = "<p>Kindly, you are requested to Change the PAM File Number for Job Applicant: {0}  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
    create_notification_log(subject, message, [grd_supervisor], job_Applicant)

@frappe.whitelist()
def notify_supervisor_change_pam_designation(name):
    job_Applicant = frappe.get_doc('Job Applicant',name)
    grd_supervisor = frappe.db.get_single_value('GRD Settings','default_grd_supervisor')
    page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
    subject = _("You Are Requested to Change/Approve New PAM Designation for Applicant with Civil ID:{0} ").format(job_Applicant.one_fm_cid_number)
    message = "<p>Kindly, you are requested to Change the PAM Designation for Job Applicant: {0}  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
    create_notification_log(subject, message, [grd_supervisor], job_Applicant)

@frappe.whitelist()
def notify_operator_with_supervisor_response(name):
    """This method will notify GRD Operator with GRD supervisor response (Accept/Reject) on the PAM Number - PAM Desigantion changes for solving internal tp issues"""
    job_Applicant = frappe.get_doc('Job Applicant',name)
    grd_operator = frappe.db.get_single_value('GRD Settings','default_grd_operator_transfer')
    if job_Applicant.accept_changes == 1 and job_Applicant.reject_changes == 0:
        page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
        subject = _("Supervisor Accepted Your Changes in Job Applicant")
        message = "<p>Kindly, you are requested to mark (no internal issues) box for Job Applicant: {0} and check if candidate has external issues while transfering  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
        create_notification_log(subject, message, [grd_operator], job_Applicant)
    if job_Applicant.accept_changes == 0 and job_Applicant.reject_changes == 1:
        page_link = get_url("/desk#Form/Job Applicant/" + job_Applicant.name)
        subject = _("Supervisor Rejected Your Changes in Job Applicant and Provide Suggested Changes")
        message = "<p>Kindly, you are requested to Check Suggestions box for Job Applicant: {0} and check if candidate has external issues while transfering  <a href='{1}'></a></p>".format(job_Applicant.name,page_link)
        create_notification_log(subject, message, [grd_operator], job_Applicant)
 
