import frappe
from frappe.desk.form.assign_to import get as get_assignments

def execute():
    tasks = frappe.get_all("Task")
    
    for task in tasks:
        doc = frappe.get_doc('Task', task.name)        
        user_doc_assignments = [assignment.owner for assignment in get_assignments({'doctype': 'Task', 'name': task.name})]
        
        # If there are no assignments then skip next step
        if len(user_doc_assignments) == 0:
            continue
        
        # Append the existing doc assignments to the 'custom_assigned_to' field
        for user in user_doc_assignments:
            doc.append('custom_assigned_to', {"user": user})
        
        doc.save(ignore_permissions=True)

    frappe.db.commit()

