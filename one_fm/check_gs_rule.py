import frappe

def run():
    doc = frappe.get_doc("Assignment Rule", "Arrival - Assign General Services")
    print("GS Rule Disabled:", doc.disabled)
    print("GS Rule Document Type:", doc.document_type)
    print("GS Rule Field:", doc.get('users', [])[0].user if doc.get('users') else getattr(doc, 'field', 'N/A'))
