import frappe, json


@frappe.whitelist()
def create_issue_log(error_log):
    error_log = frappe._dict(json.loads(error_log))

    is_doctype_related = "Yes" if error_log.reference_doctype else "No"

    issue_log = frappe.get_doc({
        'doctype':'HD Ticket',
        'reference_doctype':error_log.doctype,
        'reference_name':error_log.name,
        'custom_ticket_category': "Doctype Issue" if is_doctype_related == "Yes" else "Other Issues",
        'custom_reference_doctype': error_log.reference_doctype if is_doctype_related == "Yes" else None,
        'subject':error_log.method,
        'status':'Open',
        'description':error_log.error,
        'priority': 'High',
        'ticket_type': 'Bug',
    }).insert(ignore_permissions=True)
    issue_log.add_comment("Comment", error_log.error)
    frappe.db.set_value("Error Log", error_log.name, 'hd_ticket', issue_log.name)
    return issue_log.name