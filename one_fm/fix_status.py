import frappe

def run():
    # 1. Update the DocType options for the status field
    doc = frappe.get_doc("DocType", "Arrival and Deployment")
    for field in doc.fields:
        if field.fieldname == "status":
            field.options = "Pending\nArriving\nJoined\nDid Not Arrive"
            break
    doc.save()

    # 2. Update the Workflow states to map correctly
    wf = frappe.get_doc("Workflow", "Arrival and Deployment Workflow")
    for s in wf.states:
        if s.state == "Did Not Arrive":
            s.update_value = "Did Not Arrive"
            s.update_field = "status"
    wf.save()

    frappe.db.commit()
    print("Status options and Workflow mapping updated successfully.")
