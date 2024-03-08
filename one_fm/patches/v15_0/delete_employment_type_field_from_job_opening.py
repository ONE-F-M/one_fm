import frappe

def execute():
    if frappe.db.exists('Custom Field', {'name': 'Job Opening-employment_type'}):
        frappe.db.sql("""
            delete from
                `tabCustom Field`
            where
                name='Job Opening-employment_type'
        """)
