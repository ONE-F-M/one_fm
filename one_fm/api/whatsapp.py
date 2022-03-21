import frappe
from .utils import response

@frappe.whitelist(allow_guest=True)
def log_issue(**kwargs):
    """
        create issue log from whatsapp endpoint
    """
    data = frappe.form_dict.copy()
    frappe.set_user('administrator')
    if data.issue_creator_email and data.issue_desc:
        try:
            issue = frappe.get_doc(dict(
                doctype = 'Issue',
                subject = data.issue_subject,
                description = f"Name: {data.issue_creator_name}\n\n"+data.issue_desc,
                raised_by = data.issue_creator_email,
            ))
            print(issue.as_dict())
            issue.flags.ignore_mandatory = True
            issue.insert(ignore_permissions=True)
            return response(
                code=200, title='Issue logged successfully',
                msg = f"Your issue has been logged,\nissue id: {issue.name}"
            )
        except Exception as e:
            print(e)
            response(
                code=500, title='Error',
                msg = f"An error occurred"
                )
    else:
        return response(
            code=500, title='Incomplete data set',
            msg = f"You provided an incomplete data set."
            )
