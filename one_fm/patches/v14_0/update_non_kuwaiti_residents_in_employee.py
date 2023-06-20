import frappe


def execute():
    try:
        db = frappe.database.get_db()
        if 'non_kuwaiti_residents' in db.get_table_columns("Employee"):
            frappe.db.sql(
                """UPDATE `tabEmployee` SET non_kuwaiti_residents = 1 WHERE employment_type = 'Service Provider'""")
    except:
        pass
