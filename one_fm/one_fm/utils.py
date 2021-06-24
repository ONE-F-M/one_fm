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
            doc.one_fm_grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
            page_link = get_url("/desk#List/Job Applicant/" + doc.name)
            message = "<p>Check If {0} Is Transferable <a href='{1}'></a>.</p>".format(doc.applicant_name,page_link)
            subject = 'Check If {0} Is Transferable '.format(doc.applicant_name)
            send_email(doc, [doc.one_fm_grd_operator], message, subject)
            create_notification_log(subject, message, [doc.one_fm_grd_operator], doc)

@frappe.whitelist()
def read_civil_id_image(doc, method):
    if doc.one_fm_has_issue == "No":
        employee = frappe.get_doc('Job Applicant',doc.name)
        for document in employee.one_fm_documents_required:
            if document.document_required == "Civil ID":
                doc.db_set('one_fm_civil_id_image', document.document_required)
            if document.document_required  == "Previous Company Authorised Signatory":
                doc.db_set('one_fm_previous_company_authorized_signatory', document.document_required)

@frappe.whitelist()
def send_recruiter_notification_with_type_of_issues(doc, method):
    if doc.one_fm_has_issue == "Yes":
        if not doc.one_fm_recruiter:
            doc.one_fm_recruiter = frappe.db.get_single_value("GRD Settings", "default_grd_operator")###will be changed
            page_link = get_url("/desk#List/Job Applicant/" + doc.name)
            message = "<p>Tranfer Process to {0} has issues<a href='{1}'></a>.</p>".format(doc.applicant_name,page_link)
            subject = 'Check If {0} Is Transferable '.format(doc.applicant_name)
            send_email(doc, [doc.one_fm_grd_operator], message, subject)
            create_notification_log(subject, message, [doc.one_fm_grd_operator], doc)##

@frappe.whitelist()
def get_signatory_name(parent):
	name_list,sign = frappe.db.sql("""select  authorized_signatory_name_arabic,signature from `tabPAM Authorized Signatory Table`
				where parent = %s """,(parent),as_list=1)
	return name_list,sign
