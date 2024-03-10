import frappe


def execute():
    frappe.db.sql("""
                  UPDATE `tabShiftPermission`
                  SET wokflow_state = "Pending Approver"
                  WHERE workflow_state = "Pending"  
                  """)