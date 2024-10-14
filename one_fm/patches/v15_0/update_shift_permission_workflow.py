import frappe


def execute():
    frappe.db.sql("""
                  UPDATE `tabShift Permission`
                  SET workflow_state = "Pending Approver"
                  WHERE workflow_state = "Pending"  
                  """)