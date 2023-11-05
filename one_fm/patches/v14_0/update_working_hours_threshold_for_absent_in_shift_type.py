import frappe

def execute():
    # update the working_hours_threshold_for_absent
    frappe.db.sql(f""" update `tabShift Type` set working_hours_threshold_for_absent = 4""") 