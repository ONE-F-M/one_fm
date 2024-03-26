import frappe
from json import dumps
import re
from httplib2 import Http

def validate(doc, event):
    doc.issue_type = "Technical Issue"
    sla_list = frappe.db.get_list("Service Level Agreement",
        {
            "enabled": 1,
            "document_type": "Issue",
        })
    if sla_list:
        doc.service_level_agreement = sla_list[0].name

def send_google_chat_notification(doc, method):
    """Hangouts Chat incoming webhook to send the Issues Created, in Card Format."""

    # Fetch the Key and Token for the API
    default_api_integration = frappe.get_doc("Default API Integration")

    if not default_api_integration:
        return

    if not default_api_integration.integration_setting:
        return

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

def send_open_issue_count_to_google_chat_notification(doc, method):
	query = frappe.db.sql("""
		SELECT COUNT(status) as status_count FROM `tabIssue` WHERE status='Open' AND DATEDIFF(NOW(), modified)>0;
	""", as_dict=1)


	if query[0].status_count:
		# Fetch the Key and Token for the API
		default_api_integration = frappe.get_doc("Default API Integration")

		google_chat = frappe.get_doc("API Integration",
			[i for i in default_api_integration.integration_setting
				if i.app_name=='Google Chat'][0].app_name)

		# Construct the request URL
		url = f"""{google_chat.url}/spaces/{google_chat.api_parameter[0].get_password('value')}/messages?key={google_chat.get_password('api_key')}&token={google_chat.get_password('api_token')}"""

		# Construct Message Body
		message = f"""<b>There are {query[0].status_count} open issue(s) that have not been replied to in the last 24 hour</b><br>"""

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
