import frappe

def execute():
    frappe.db.sql("DELETE from `tabCustom Field` where name = 'Shift Request-assign_day_off'")