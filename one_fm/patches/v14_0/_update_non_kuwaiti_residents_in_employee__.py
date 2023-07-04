import frappe


def execute():
    frappe.db.sql("""UPDATE `tabEmployee` SET is_in_kuwait = 1 WHERE employment_type != 'Service Provider'""")
    frappe.db.sql("""UPDATE `tabEmployee` SET is_in_kuwait = 0 WHERE employment_type = 'Service Provider'""")
    
