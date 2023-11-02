import frappe


def execute():
    query = "UPDATE `tabAttendance Check` SET justification = '' WHERE attendance_status != 'Present'"
    frappe.db.sql(query)