# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
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
    if doc.one_fm_is_transferable == 'Yes' and doc.one_fm_cid_number and doc.one_fm_passport_number: 
        notify_grd_to_check_applicant_documents(doc)

    if doc.one_fm_has_issue and doc.one_fm_notify_recruiter == 0:
        notify_recruiter_after_checking(doc)

def notify_grd_to_check_applicant_documents(doc):
    """
    This method is notifying all operators with applicant's cid and passport to check on PAM,
    This method runs on update, so if the notification had sent before it won't annoy the operators again
     by checking notification log list.
    """
    filtered_grd_users = []
    find = False
    users = get_users_with_role('GRD Operator') 
    for user in users:
        filtered_grd_users.append(user)
        find = True
        break
    if find and filtered_grd_users and len(filtered_grd_users) > 0:  
        dt = frappe.get_doc('Job Applicant',doc.name)
    if dt:
        email = filtered_grd_users
        page_link = get_url("/desk#List/Job Applicant/" + dt.name)
        message = "<p>Check If Transferable.<br>Civil id:{0} - Passport Number:{1}<a href='{2}'></a>.</p>".format(dt.one_fm_cid_number,dt.one_fm_passport_number,page_link)
        subject = 'Check If Transferable.<br>Civil id:{0} - Passport Number:{1}'.format(dt.one_fm_cid_number,dt.one_fm_passport_number)
        send_email(dt, email, message, subject)

        if not frappe.db.exists("Notification Log",{'subject':subject,'document_type':"Job Applicant"}):
        # check if the notification have been sent before.
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
    filtered_recruiter_users = []
    find = False
    users = get_users_with_role('Recruiter')
    for user in users:
        filtered_recruiter_users.append(user)
        find = True
        break 
    if find and filtered_recruiter_users and len(filtered_recruiter_users) > 0:  
        dt = frappe.get_doc('Job Applicant',doc.name)
    if dt:
        if dt.one_fm_has_issue == "Yes" and dt.one_fm_notify_recruiter == 0:
            email = filtered_recruiter_users
            page_link = get_url("/desk#List/Job Applicant/" + dt.name)
            message="<p>Tranfer for {0} has issue<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
            subject='Tranfer for {0} has issue'.format(dt.applicant_name)
            create_notification_log(subject,message,email,dt)
            dt.db_set('one_fm_notify_recruiter', 1)
            dt.db_set('status', "Checked By GRD")

        if dt.one_fm_has_issue == "No" and dt.one_fm_notify_recruiter == 0: 
            email = filtered_recruiter_users
            page_link = get_url("/desk#List/Job Applicant/" + dt.name)
            message="<p>Tranfer for {0} has no issue<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
            subject='Tranfer for {0} has no issues'.format(dt.applicant_name)
            create_notification_log(subject,message,email,dt)
            dt.db_set('one_fm_notify_recruiter', 1)
            dt.db_set('status', "Checked By GRD")

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
                frappe.throw("Set The Type of Transfer issue Applicant has before saving")
    if "Recruiter" or "Senior Recruiter" in roles:
        if doc.one_fm_is_transferable == "Yes":
            validate_mendatory_fields_for_recruiter(doc)
            
                
def validate_mendatory_fields_for_grd(doc):
    """
        Check all the mendatory fields are set set by grd
    """
    field_list = [{'PAM File Number':'one_fm_pam_file_number'}, {'PAM Designation':'one_fm_pam_designation'}, 
            {'Authorized Signatory':'one_fm_authorized_signatory'}, {'Signatory Name':'one_fm_signatory_name'}]

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
    field_list = [{'CIVIL ID':'one_fm_cid_number'}, {'Date of Birth':'one_fm_date_of_birth'}, 
            {'Gender':'one_fm_gender'}, {'Religion':'one_fm_religion'},
            {'Nationality':'one_fm_nationality'}, {'Designation':'one_fm_previous_designation'}, 
            {'Passport Number':'one_fm_passport_number'}, {'What is Your Highest Educational Qualification':'one_fm_educational_qualification'},
            {'Marital Status':'one_fm_marital_status'}, {'Work Permit Salary':'one_fm_work_permit_salary'},
            {'Last Working Date':'one_fm_last_working_date'}, {'Date of Entry':'one_fm_date_of_entry'}]

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
def get_signatory_name(parent):
    name_list = frappe.get_doc('PAM Authorized Signatory List',parent)
    names=[]
    for line in name_list.authorized_signatory:
        if line.authorized_signatory_name_arabic:
            names.append(line.authorized_signatory_name_arabic)
    return names
   
