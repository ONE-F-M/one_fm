import frappe


def execute():
    # fix employee customizations
    frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name='Salary Structure Assignment-section_break_17';")
    frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name='Employee-column_break_104';")