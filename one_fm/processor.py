import frappe
import requests
import json
from twilio.rest import Client as TwilioClient
import xml.etree.ElementTree as ET
from frappe.utils.jinja import (get_email_from_template)
from frappe.desk.doctype.notification_settings.notification_settings import(
	is_notifications_enabled,
	is_email_notifications_enabled
)

@frappe.whitelist()
def sendemail(recipients, subject, header=None, message=None,
	content=None, reference_name=None, reference_doctype=None,
	sender=None, cc=None , attachments=None, delayed=False, args=None, template=None, is_external_mail=False,is_scheduler_email=False, expose_recipients=None):
	logo = "https://one-fm.com/files/ONEFM_Identity.png"
	template = "default_email"
	actions=pdf_link=workflow_state=""
	doc_link = "#"
	mandatory_field = None
	field_labels = None
	head = header[0] if header else ""

	if not message:
		message = " "

	# If scheduler event email then check for its trigger from "ONEFM General Setting"
	if is_scheduler_email:
		is_scheduler_emails_enabled = frappe.db.get_single_value("ONEFM General Setting", "enable_scheduler_event_emails")

		if not is_scheduler_emails_enabled:
			return

	if recipients and "Administrator" in recipients:
		if isinstance(recipients, list):
			recipients.remove("Administrator")
		else:
			recipients = recipients.replace("Administrator", "")

	if args:
		template = "default_email_with_workflow"
		head = "Workflow Action"
		actions = args.get("actions")
		message = args.get("message")
		pdf_link = args.get("pdf_link")
		doc_link = args.get("doc_link")
		workflow_state = args.get("workflow_state")
		mandatory_field = args.get("mandatory_field")
		field_labels = args.get("field_labels")

	if type(recipients) == str:
		recipients = [recipients]

	if not is_external_mail:
		recipients = [recipient for recipient in recipients if is_email_notifications_allowed(recipient)]
		if not sender:
			sender = "Administrator"

	if recipients and len(recipients) > 0:
		frappe.sendmail(template = template,
			recipients=recipients,
			sender= sender,
			cc=cc,
			subject=subject,
			args=dict(
				header=head,
				subject=subject,
				message=message,
				content=content,
				reference_name= reference_name,
				reference_doctype = reference_doctype,
				logo=logo,
				actions=actions,
				pdf_link=pdf_link,
				doc_link=doc_link,
				workflow_state=workflow_state,
				mandatory_field=mandatory_field,
				field_labels=field_labels
			),
			attachments = attachments,
			delayed=delayed,
			expose_recipients=expose_recipients
		)

def is_email_notifications_allowed(user):
    """
    The method check if email notifications are allowed for a given user.
    Args:
        user (str): The user's email.
    Returns:
        bool: True if email notifications are allowed, otherwise False.
    """

	# Check if general notifications are enabled for the user
    if not is_notifications_enabled(user):
        return False  # Return False if notifications are disabled

    # Check if email notifications specifically are enabled for the user
    if not is_email_notifications_enabled(user):
        return False  # Return False if email notifications are disabled

    # Check if the user's email is the preferred company email in the Employee record
    if not is_user_id_company_prefred_email_in_employee(user):
        return False  # Return False if it's not the preferred email

    # If all conditions pass, return True (email notifications are allowed)
    return True

@frappe.whitelist()
def is_user_id_company_prefred_email_in_employee(user_id):
	'''
	Check if user_id is an active employee's company email set as preferred contact.
	Args:
		user_id: email id (Text/Email)
	Returns:
		True if user_id matches an active employee's company email with Company Email preference
		False otherwise
	'''
	employee = frappe.db.get_value(
		"Employee",
		{
			"user_id": user_id,
			"status": "Active",
			"prefered_contact_email": "Company Email",
			"company_email": user_id,
			"prefered_email": user_id
		},
		["name"],
		as_dict=1
	)

	if not employee:
		return False

	return True

@frappe.whitelist()
def send_whatsapp(sender_id, template_name, content_variables):
	twilio = frappe.get_doc('Twilio Setting')
	content_sid = frappe.get_value('Content Template', {'template_name':template_name}, ['content_sid'])

	client =  TwilioClient(twilio.sid, twilio.token)

	if content_sid:
		message = client.messages.create(
								from_='whatsapp:' + twilio.t_number,
								messaging_service_sid=twilio.messaging_service_sid,
								content_sid=content_sid,
								content_variables=json.dumps(content_variables),
								to='whatsapp:+'+sender_id
							)

	return message

@frappe.whitelist(allow_guest=True)
def whatsapp():
	possibility = " "
	if(frappe.request.data):
		data = decode_data(frappe.request.data)
		body = data["Body"]
		from_ = data["WaId"]

		res = send_whatsapp(sender_id=from_, body=body)

	return '200'

def decode_data(data):
    """Fetched Data from request is in form of bytes.
    This function is to convert Bytes to string and then into Dictionary

    Args:
        data (bytes): the data fetched from the request made to the given method.

    Returns:
        dict_data: dictionary consisting keys and values from data
    """
    decode_data = data.decode("utf-8")
    dict_data = {}
    lists = list(decode_data.split("&"))
    for l in lists:
        dict_data[l.split("=")[0]]= l.split("=")[1]
    return dict_data
