# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe.utils import today, add_days, get_url
from frappe.integrations.offsite_backup_utils import get_latest_backup_file, send_email, validate_file_size, get_chunk_site
from one_fm.api.notification import create_notification_log

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
    if doc.one_fm_is_transferable == "Yes":
        
        if not doc.one_fm_grd_operator:
            doc.one_fm_grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
        print(doc.name)
        dt = frappe.get_doc('Job Applicant',doc.name)
        if dt:
            page_link = get_url("/desk#List/Job Applicant/" + dt.name)
            message = "<p>Check If {0} Is Transferable.<br>Civil id:{1} - Passport Number:{2}<a href='{3}'></a>.</p>".format(dt.applicant_name,dt.one_fm_cid_number,dt.one_fm_passport_number,page_link)
            subject = 'Check If {0} Is Transferable.<br>Civil id:{1} - Passport Number:{2}'.format(dt.applicant_name,dt.one_fm_cid_number,dt.one_fm_passport_number)
            send_email(dt, [dt.one_fm_grd_operator], message, subject)
            create_notification_log(subject, message, [dt.one_fm_grd_operator], dt)

@frappe.whitelist()
def send_recruiter_notification_with_type_of_issues(doc, method):
    if doc.one_fm_has_issue == "Yes":
        users = [], set_user = False
        for role in frappe.get_roles(frappe.session.user):
            if role == "Senior Recruiter" or role == "Recruiter":
                set_user = True
        if set_user:
            users.append(frappe.session.user)
        dt = frappe.get_doc('Job Applicant',doc.name)
        if dt:
            email = users
            page_link = get_url("/desk#List/Job Applicant/" + dt.name)
            subject = 'Tranfer for {0} has issues'.format(dt.applicant_name)
            message = "<p>Tranfer for {0} has issues<a href='{1}'></a>.</p>".format(dt.applicant_name,page_link)
            create_notification_log(subject,message,email,dt)

@frappe.whitelist()
def get_signatory_name(parent):
    name_list = frappe.get_doc('PAM Authorized Signatory List',parent)
    names=[]
    for line in name_list.authorized_signatory:
        if line.authorized_signatory_name_arabic:
            names.append(line.authorized_signatory_name_arabic)
    return names
   
