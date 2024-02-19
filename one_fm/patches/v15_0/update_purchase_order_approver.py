import frappe


def execute():
    frappe.db.sql("""
                    UPDATE `tabPurchase Order`
                    SET custom_purchase_order_approver = department_manager 
                """)