import frappe
from frappe.utils.file_manager import upload
from .utils import response
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def log_issue(**kwargs):
    """
        create issue log from whatsapp endpoint
    """
    data = frappe.form_dict.copy()
    frappe.set_user('administrator')
    if data.issue_creator_email and data.issue_desc:
        try:
            # if valid data create issue
            issue = frappe.get_doc(dict(
                doctype = 'Issue',
                subject = data.issue_subject,
                description = f"Name: {data.issue_creator_name}<br>"+data.issue_desc,
                raised_by = data.issue_creator_email,
            ))
            issue.flags.ignore_mandatory = True
            issue.insert(ignore_permissions=True)
            # if media available, attach it
            if data.issue_media:
                frappe.form_dict.doctype = 'Issue'
                frappe.form_dict.docname = issue.name
                frappe.form_dict.file_url = data.issue_media
                frappe.form_dict.is_private = True
                frappe.form_dict.filename = data.issue_creator_name+ "-" + "media-" + str(datetime.now())
                upload()
                # add image to description
                if 'image' in data.issue_media_type:
                    issue.db_set('description',
                        issue.description + "<br>" + f'<img height="300px" width="300px" src="{data.issue_media}" />')

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
