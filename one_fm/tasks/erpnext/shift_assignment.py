import frappe



def before_insert(doc, events):
    """
        Before insert events to execute
    """
    if not frappe.db.exists("Employee", {'name':doc.employee, 'status':'Active'}):
        frappe.throw(f"{doc.employee} - {doc.employee_name} is not active and cannot be assigned to a shift")
