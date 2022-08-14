from __future__ import unicode_literals
import frappe

def execute():
    frappe.enqueue(update_workflowstate, queue='long')

#This Function is patch to update the Workflow State from ''Draft' to 'Open'. 
def update_workflowstate():
    leave_list = frappe.get_list("Leave Application", {"workflow_state":"Draft"},["name"])
    for leave in leave_list:
        frappe.set_value("Leave Application", leave.name, "workflow_state", "Open")
    frappe.db.commit() 