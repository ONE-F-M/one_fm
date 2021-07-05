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
def send_grd_notification_to_check_applicant_document(doc, method):
    filtered_users = []
    if doc.one_fm_is_transferable == "Yes" and doc.one_fm_notify_operator == 0: 
        users = get_users_with_role('GRD Operator') 
        for user in users:
            filtered_users.append(user)
        if filtered_users and len(filtered_users) > 0:  
            dt = frappe.get_doc('Job Applicant',doc.name)
            if dt:
                # print(dt.one_fm_notify_operator)
                email = filtered_users
                page_link = get_url("/desk#List/Job Applicant/" + dt.name)
                message = "<p>Check If {0} Is Transferable.<br>Civil id:{1} - Passport Number:{2}<a href='{3}'></a>.</p>".format(dt.applicant_name,dt.one_fm_cid_number,dt.one_fm_passport_number,page_link)
                subject = 'Check If {0} Is Transferable.<br>Civil id:{1} - Passport Number:{2}'.format(dt.applicant_name,dt.one_fm_cid_number,dt.one_fm_passport_number)
                send_email(dt, email, message, subject)
                create_notification_log(subject, message, email, dt)
                dt.one_fm_notify_operator = 1
                dt.save()
                # print(dt.one_fm_notify_operator)
    

@frappe.whitelist()
def send_recruiter_notification_with_type_of_issues(doc, method):
    filtered_users = []
    users = get_users_with_role('Recruiter')
    for user in users:
        filtered_users.append(user)
    if filtered_users and len(filtered_users) > 0:  
        dt = frappe.get_doc('Job Applicant',doc.name)
    if dt:
        if dt.one_fm_has_issue == "Yes" and dt.one_fm_notify_recruiter == 0:
            email = filtered_users
            page_link = get_url("/desk#List/Job Applicant/" + dt.name)
            message="<p>Tranfer for {0} has {1} issue<a href='{2}'></a>.</p>".format(dt.applicant_name,dt.one_fm_type_of_issues,page_link)
            subject='Tranfer for {0} has issues'.format(dt.applicant_name)
            create_notification_log(subject,message,email,dt)
        if dt.one_fm_has_issue == "No" and dt.one_fm_notify_recruiter == 0: 
            email = filtered_users
            page_link = get_url("/desk#List/Job Applicant/" + dt.name)
            message="<p>Tranfer for {0} has no issue<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
            subject='Tranfer for {0} has no issues'.format(dt.applicant_name)
            create_notification_log(subject,message,email,dt)
        
        dt.one_fm_notify_recruiter = 1
        dt.status = "Checked By GRD"
        dt.save()

@frappe.whitelist()
def get_signatory_name(parent):
    name_list = frappe.get_doc('PAM Authorized Signatory List',parent)
    names=[]
    for line in name_list.authorized_signatory:
        if line.authorized_signatory_name_arabic:
            names.append(line.authorized_signatory_name_arabic)
    return names
   
