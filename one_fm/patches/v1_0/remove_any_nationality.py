from __future__ import unicode_literals
import frappe

def execute():
    frappe.db.sql("""UPDATE `tabERF Gender Height Requirement` SET nationality='No Nationality' WHERE nationality='Any';""")
    frappe.db.sql("""DELETE FROM `tabNationality` WHERE name='Any';""")
    try:
        frappe.get_doc({
            'doctype': 'Nationality',
            'nationality_english': 'No Nationality',
            'country': 'لا جنسية',
        }).insert(ignore_permissions=True)
    except:
        pass