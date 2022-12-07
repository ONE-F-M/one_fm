import frappe


def execute():
    frappe.db.sql("""DELETE from `tabCustom Field` WHERE name='Employee-salary_structure';""")
    