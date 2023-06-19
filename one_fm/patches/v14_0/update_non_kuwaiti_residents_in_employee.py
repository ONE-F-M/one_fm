import frappe

def execute():
    frappe.db.sql("""UPDATE `tabEmployee` SET non_kuwaiti_residents = 1 WHERE employment_type = 'Service Provider'""")
