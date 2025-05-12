import frappe

def create_workflow(workflow_data):
    existing = frappe.db.exists("Workflow", {"workflow_name": workflow_data["workflow_name"]})
    if not existing:
        frappe.get_doc(workflow_data).insert()
    else:
        doc = frappe.get_doc("Workflow", {"workflow_name": workflow_data["workflow_name"]})
        doc.update(workflow_data)
        doc.save()
