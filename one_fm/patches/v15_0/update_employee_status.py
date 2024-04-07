import frappe

def execute():
    """Update the employee status of staff currently on leave"""
    active_staff = frappe.get_all("Employee",{'status':"Active"})
    if active_staff:
        active_staff = [i.name for i in active_staff]
        today = frappe.utils.today()
        affected_leaves = frappe.get_all("Leave Application",{'from_date':['<=',today],'to_date':['>=',today],'employee':['IN',active_staff],'status':"Approved",'docstatus':1},['employee'])
        if affected_leaves:
            for one in affected_leaves:
                frappe.db.set_value("Employee",one.employee,'status','Vacation')
                
