import frappe


def execute():
    frappe.db.sql("""UPDATE `tabEmployee` SET is_in_kuwait = 0 WHERE employment_type = 'Service Provider'""")
    try:
        db = frappe.database.get_db()
        if 'non_kuwaiti_residents' in db.get_table_columns("Employee"):
            frappe.db.sql(
                """UPDATE `tabEmployee` SET non_kuwaiti_residents = 1 WHERE employment_type = 'Service Provider'""")
    except:
        pass
