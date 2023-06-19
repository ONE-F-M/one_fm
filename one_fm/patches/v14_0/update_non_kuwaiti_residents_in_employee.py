import frappe


def execute():
    db = frappe.databse.get_db()
    if 'non_kuwaiti_residents' in db.get_table_columns("Employee"):
        frappe.db.sql(
            """UPDATE `tabEmployee` SET non_kuwaiti_residents = 1 WHERE employment_type = 'Service Provider'""")
