from __future__ import unicode_literals
import frappe

def execute():
    frappe.enqueue(update_workflowstate, queue='long')

#This Function is patch to update the Notification log with category, title and body. 
def update_workflowstate():
    frappe.db.sql("""UPDATE `tabLeave Application` SET workflow state='Open' WHERE workflow state='Draft';""")