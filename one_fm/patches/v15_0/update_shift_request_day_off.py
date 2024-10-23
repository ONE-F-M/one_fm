import frappe


def execute():
    frappe.db.sql("""
        UPDATE `tabShift Request`
        SET purpose = "Assign Day Off"
        WHERE assign_day_off = 1       
        """)