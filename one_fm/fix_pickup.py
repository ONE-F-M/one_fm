import frappe

def run():
    doc = frappe.get_doc("DocType", "Arrival and Deployment")
    for field in doc.fields:
        if field.fieldname == "pickup_contact":
            field.fieldtype = "Link"
            field.options = "Employee"
            break
    doc.save()
    frappe.db.commit()
    print("pickup_contact changed to Link -> Employee.")
