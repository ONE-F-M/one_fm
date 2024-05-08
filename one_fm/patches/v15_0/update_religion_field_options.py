import frappe

def update_religion_field(doctype, fieldname):
    query = """
        UPDATE `tab{}` 
        SET `{}` = 'Muslim' 
        WHERE `{}` = 'Islam'
    """.format(doctype, fieldname, fieldname)

    frappe.db.sql(query)

def delete_religion_option(name):
    query = """
        DELETE FROM `tabReligion`
        WHERE  religion = '{}'
    """.format(name)

    frappe.db.sql(query)

def execute():
    # Update religion field value from 'Islam' to 'Muslim'
    update_religion_field('Bed', 'religion')
    update_religion_field('Book Bed', 'religion')
    update_religion_field('Work Permit', 'religion')
    update_religion_field('Onboard Employee', 'religion')
    update_religion_field('Transfer Paper', 'religion')
    update_religion_field('Employee', 'one_fm_religion')
    update_religion_field('Job Applicant', 'one_fm_religion')
    update_religion_field('PAM Visa', 'religion')

    # Delete 'Islam' from religion options
    delete_religion_option('Islam')
    
    frappe.db.commit()