from __future__ import unicode_literals
import frappe

def execute():
    frappe.enqueue(update_workflowstate, queue='long')

#This Function is patch to update the Workflow State from ''Draft' to 'Open'. 
def update_workflowstate():
    frappe.db.sql("""UPDATE `tabLeave Application` SET workflow_state='Open' WHERE workflow_state='Draft';""")