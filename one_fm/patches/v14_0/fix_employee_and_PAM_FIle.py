import frappe


def execute():
    frappe.db.sql("""DELETE from `tabCustom Field` WHERE name='Employee-pam_visa';""")
    frappe.db.sql("""DELETE from `tabCustom Field` WHERE name='Employee-pam_authorized_signatory';""")