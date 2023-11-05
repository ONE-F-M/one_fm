import frappe, json


@frappe.whitelist()
def create_issue_log(error_log):
    error_log = frappe._dict(json.loads(error_log))

    issue_log = frappe.get_doc({
        'doctype':'Issue',
        'reference_doctype':error_log.doctype,
        'reference_name':error_log.name,
        'subject':error_log.method,
        'status':'Open',
        'priority': 'Shits on Fire!',
        'issue_type': 'Bug',
    }).insert(ignore_permissions=True)
    issue_log.add_comment("Comment", error_log.error)
    frappe.db.set_value("Error Log", error_log.name, 'issue_log', issue_log.name)
    return issue_log.name