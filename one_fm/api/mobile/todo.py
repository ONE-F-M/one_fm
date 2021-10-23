import frappe

@frappe.whitelist()
def get_call(status,priority,description,allocate_to):
    doc = frappe.new_doc('ToDo')
    doc.status = status
    doc.priority = priority
    doc.description = description
    doc.owner = allocate_to
    doc.save()

    return doc

