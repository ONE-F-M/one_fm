import frappe

def execute():
    # update the working_hours_threshold_for_absent
    frappe.db.sql(f""" UPDATE `tabTimesheet` SET status = 'Submitted' WHERE workflow_state = 'Approved' """) 