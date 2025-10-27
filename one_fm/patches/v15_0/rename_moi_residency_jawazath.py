import frappe

def execute():
    # Copy data from old table to new table
    frappe.db.rename_table("MOI Residency Jawazat", "Residency")