import frappe
from frappe.utils import getdate
from json import dumps
from httplib2 import Http
from frappe.desk.form.assign_to import add as add_assignment

from one_fm.processor import sendemail

def send_google_chat_notification(doc, method):
    """Hangouts Chat incoming webhook to send the Issues Created, in Card Format."""

    # Fetch the Key and Token for the API
    default_api_integration = frappe.get_doc("Default API Integration")

    google_chat = frappe.get_doc("API Integration",
        [i for i in default_api_integration.integration_setting
            if i.app_name=='Google Chat'][0].app_name)

    if google_chat.active:
        # Construct the request URL
        url = f"""{google_chat.url}/spaces/{google_chat.api_parameter[0].get_password('value')}/messages?key={google_chat.get_password('api_key')}&token={google_chat.get_password('api_token')}"""

        # Construct Message Body
        message = f"""<b>A new Issue has been created</b><br>
            <i>Details:</i> <br>
            Subject: {doc.subject} <br>
            Name: {doc.name} <br>
            Raised By (Email): {doc.raised_by} <br>
            Body: {doc.description}<br>
            """

        # Construct Card the allows Button action
        bot_message = {
            "cards_v2": [
                {
                "card_id": "IssueCard",
                "card": {
                "sections": [
                {
                    "widgets": [
                        {
                        "textParagraph": {
                        "text": message
                        }
                        },
                    {
                    "buttonList": {
                        "buttons": [
                        {
                            "text": "Open Document",
                            "onClick": {
                            "openLink": {
                                "url": frappe.utils.get_url(doc.get_url()),
                            }
                            }
                        },
                        ]
                    }
                    }
                ]
                }
                ]
            }
            }
            ]
        }

        # Call the API
        message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
        http_obj = Http()
        response = http_obj.request(
            uri=url,
            method='POST',
            headers=message_headers,
            body=dumps(bot_message),
        )


def validate_hd_ticket(doc, event):
    bug_buster = frappe.get_all("Bug Buster",{'docstatus':1,'from_date':['<=',getdate()],'to_date':['>=',getdate()]},['employee'])
    if bug_buster:
        emp_user = frappe.get_value("Employee",bug_buster[0].employee,'user_id')
        if emp_user:
            doc.custom_bug_buster = emp_user


def notify_ticket_raiser_of_receipt(doc, event):
    subject = f"HelpDesk Ticket - {doc.name}"
    context = dict(
        document_name=doc.name,
        document_link=frappe.utils.get_url(doc.get_url()),
        document_subject=doc.subject
    )
    msg = frappe.render_template('one_fm/templates/emails/notify_ticket_raiser_receipt.html', context=context)
    frappe.enqueue(method=sendemail, queue="short", recipients=doc.raised_by, subject=subject, content=msg, is_external_mail=True, is_scheduler_email=True)