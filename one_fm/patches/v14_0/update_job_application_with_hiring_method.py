import frappe


def execute():
    query = "UPDATE `tabJob Applicant` SET one_fm_hiring_method = 'Buffet Recruitment' WHERE one_fm_hiring_method = 'Bulk Recruitment'"
    frappe.db.sql(query)