import frappe

def validate(doc, event):
    doc.issue_type = "Technical Issue"
    sla_list = frappe.db.get_list("Service Level Agreement",
        {
            "enabled": 1,
            "document_type": "Issue",
        })
    if sla_list:
        doc.service_level_agreement = sla_list[0].name
