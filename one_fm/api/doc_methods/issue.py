import html, re, xml
import requests, frappe
from twilio.rest import Client as TwilioClient

@frappe.whitelist()
def log_pivotal_tracker():
    """
        Update Issue Doctype with payload from Pivotal Tracker
    """
    try:
        doc = frappe.get_doc("Issue", frappe.form_dict.name)
        doc_link = frappe.utils.get_url()+doc.get_url()
        default_api_integration = frappe.get_doc("Default API Integration")

        pivotal_tracker = frappe.get_doc("API Integration",
            [i for i in default_api_integration.integration_setting
                if i.app_name=='Pivotal Tracker'][0].app_name)

        headers={"X-TrackerToken":pivotal_tracker.get_password('api_token').replace(' ', ''),
            "Content-Type": "application/json"}
        project_id = pivotal_tracker.get_password('project_id').replace(' ', '')
        url = f"{pivotal_tracker.url}/services/v5/projects/{project_id}/stories"
        print(url)
        # escape HTML in description
        TAG_RE = re.compile(r'<[^>]+>')
        description = TAG_RE.sub('', doc.description)
        req = requests.post(
            url=url,
            headers=headers,
            json={"name":doc.subject,
               'description':f"""Link:\t{doc_link}\nStatus: \t{doc.status}\nPriority: \t{doc.priority}\nIssue Type: \t{doc.issue_type}\n\n
               {description}""",
               'story_type':'bug',},
            timeout=5
        )
        if(req.status_code==200):
            response_data = frappe._dict(req.json())
            doc.db_set('pivotal_tracker', f"{pivotal_tracker.url}/n/projects/{project_id}/stories/{response_data.id}")
            return {'status':'success'}
        else:
            frappe.throw(f"Pivotal Tracker story could not be created:\n {req.json()}")
    except Exception as e:
        frappe.throw(f"Pivotal Tracker story could not be created:\n {str(e)}")
        frappe.log_error(str(e), 'Issue Pivotal Tracker')


# SEND REPLY TO WHATSAPP
@frappe.whitelist()
def whatsapp_reply_issue(**kwargs):
    """
        Reply to issues created from whatsapp
        Add comment to Issue
    """
    try:
        # send WhatsApp
        sid, t_number, auth_token = frappe.db.get_value('Twilio Setting', filters=None, fieldname=['sid','token','t_number'])
        client = TwilioClient(sid, auth_token)
        From = 'whatsapp:+14155238886'# + t_number
        to = 'whatsapp:' + frappe.form_dict.recipient
        body = frappe.form_dict.message

        message = client.messages.create(
        from_=From,
        body=body,
        to=to
        )
        # add to issue comment
        issue_comment = frappe.get_doc(dict(
        doctype='Comment',
        comment_type='Comment',
        subject='Whatsapp Reply '+frappe.form_dict.recipient,
        content=frappe.form_dict.message,
        reference_doctype='Issue',
        link_doctype='Issue',
        reference_name=frappe.form_dict.doc,
        link_name=frappe.form_dict.doc
        )).insert(ignore_permissions=1)
        return True
    except Exception as e:
        frappe.log_error(str(e), 'Issue Whatsapp Reply')
        return False
