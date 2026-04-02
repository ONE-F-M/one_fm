import frappe

def execute():
    frappe.db.add_index("Attendance", ["leave_application"])