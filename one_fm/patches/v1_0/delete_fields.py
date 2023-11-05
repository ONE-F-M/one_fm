from __future__ import unicode_literals
import frappe

def execute():
    columns = ("one_fm_applicant_civil_id", "one_fm_passport_applicant_number", "one_fm_previous_company_authorized_signatory", "one_fm_recruiter")
    for column in columns:
        if column in frappe.db.get_table_columns("Job Applicant"):
            frappe.db.sql("alter table `tabJob Applicant` drop column {0}".format(column))
        

