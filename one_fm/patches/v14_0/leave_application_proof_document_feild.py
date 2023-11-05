import frappe

def execute():
    p_doc = frappe.get_list("Leave Application", {"proof_document":("!=","")},["*"])
    for p in p_doc:
        doc = frappe.get_doc("Leave Application", p.name)
        if p.proof_document:
            doc.append("proof_documents",{"attachments": p.proof_document})
        doc.proof_document = ""
        if doc.status in ["Accepted", "Rejected","Cancelled"]:
            doc.submit()
        else:
            doc.save()
        frappe.db.commit()