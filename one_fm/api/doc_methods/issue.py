import html, re, xml, json
import requests, frappe
from twilio.rest import Client as TwilioClient

@frappe.whitelist()
def log_pivotal_tracker(**kwargs):
    """
        Update Issue Doctype with payload from Pivotal Tracker
    """
    try:
        TAG_RE = re.compile(r'<[^>]+>')
        doc = frappe.get_doc("Issue", frappe.form_dict.name)
        if frappe.form_dict.comments:
            comments = json.loads(frappe.form_dict.comments)
            description = """"""
            for i in comments:
                i['comment'].replace('ql-editor read-mode', '')
                description += f"""<br><br>{i['comment']}"""
            description = TAG_RE.sub('', description)
        else:
            description = TAG_RE.sub('', doc.description)

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

def notify_issue_raiser(doc, method):
    """This method notifies the issue raiser via email upon creating an issue."""

    from one_fm.processor import sendemail

    try:
        if doc.raised_by and doc.communication_medium in ["System", "Email", "Mobile App"]:

            issue_id = doc.name
            issue_subject = doc.subject
            email_subject = f"ONE FM Support - {issue_id}"

            header = ['Support Ticket', 'blue']

            message = f"""
            Dear user, <br><br>
            Thank you for contacting our support team. A support ticket has now been opened for your request.<br>
            You will be notified when a response is made by email. The details of your ticket are shown below:<br>
            <br>
            Issue ID: {issue_id}<br>
            Issue subject: {issue_subject}<br><br>
            """

            sendemail(recipients=[doc.raised_by], subject=email_subject, header=header, message=message)

    except Exception as error:
        frappe.log_error(error)
