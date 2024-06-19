import frappe

def execute():
    """Submit all shift permissions for 20th,21st and 22nd of May 2024"""
    all_shift_permissions = frappe.get_all("Shift Permission",{"docstatus":0,'date':['in',['2024-05-20','2024-05-21','2024-05-22']]})
    if all_shift_permissions:
        for each in all_shift_permissions:
            frappe.db.set_value("Shift Permission",each.name,'workflow_state','Approved')
            frappe.db.set_value("Shift Permission",each.name,'docstatus',1)
        frappe.db.commit()