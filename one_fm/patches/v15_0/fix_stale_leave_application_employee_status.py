import frappe
from frappe.utils import today

from one_fm.one_fm.doctype.reliever_assignment.reliever_assignment import reassign_responsibilities

def execute():
    query_past_leaves = """
        SELECT DISTINCT la.employee
        FROM `tabLeave Application` la
        JOIN `tabEmployee` e ON la.employee = e.name
        WHERE la.to_date <= %s
        AND e.status = 'Vacation'
    """
    
    past_leave_employees = {row["employee"] for row in frappe.db.sql(query_past_leaves, (today(),), as_dict=True)}

    if not past_leave_employees:
        return 

    query_active_leaves = """
        SELECT DISTINCT la.employee
        FROM `tabLeave Application` la
        WHERE la.from_date <= %s AND la.to_date > %s
    """

    active_leave_employees = {row["employee"] for row in frappe.db.sql(query_active_leaves, (today(), today()), as_dict=True)}

    final_employees = past_leave_employees - active_leave_employees 
    if not final_employees:
        return 

    placeholders = ", ".join(["%s"] * len(final_employees))  
    query_final = f"""
        SELECT la.employee, la.custom_reliever_, la.name
        FROM `tabLeave Application` la
        JOIN `tabEmployee` e ON la.employee = e.name
        WHERE la.to_date <= %s
        AND e.status = 'Vacation'
        AND la.employee IN ({placeholders})
    """

    leave_applications = frappe.db.sql(
        query_final, 
        (today(), *final_employees),
        as_dict=True
    )

    if not leave_applications:
        return 
    
    
    employees_to_update = tuple(set(obj["employee"] for obj in leave_applications))
    if employees_to_update:
        frappe.db.sql("UPDATE `tabEmployee` SET status = 'Active' WHERE name IN %s", (employees_to_update,))

    for obj in leave_applications:
        employee = obj["employee"]
        reliever = obj.get("custom_reliever_")
        leave_application = obj["name"]

        if reliever and frappe.db.exists("Reliever Assignment", {"name": leave_application}):
            frappe.enqueue(reassign_responsibilities, leave_application=leave_application)