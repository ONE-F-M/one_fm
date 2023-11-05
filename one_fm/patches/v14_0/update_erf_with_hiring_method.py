import frappe


def execute():
    query = "UPDATE tabERF SET hiring_method = 'Bulk Recruitment' WHERE hiring_method = 'Bulk Recruitment'"
    frappe.db.sql(query)