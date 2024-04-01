import frappe


def execute():
    frappe.db.sql("""
                    UPDATE `tabPurchase Order`
                    SET custom_purchase_order_approver = department_manager 
                """)
    
    frappe.db.sql(""" UPDATE `tabPurchase Order`
                    SET workflow_state = 'Pending Approver'
                    WHERE workflow_state = 'Pending HOD Approval'
                  """)
    
    frappe.db.sql(""" UPDATE `tabPurchase Order`
                  SET workflow_state = 'Pending Purchase Manager'
                  WHERE workflow_state = 'Pending Procurement Manager Approval'
                  """)
    
    frappe.db.sql(""" UPDATE `tabPurchase Order`
                  SET workflow_state = 'Approved'
                  WHERE workflow_state = 'Submitted'
                  """)
    
    