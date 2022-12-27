import frappe
import requests
import json
from twilio.rest import Client as TwilioClient
import xml.etree.ElementTree as ET
from frappe.utils.jinja import (get_email_from_template)

@frappe.whitelist()
def sendemail(recipients, subject, header=None, message=None,
	content=None, reference_name=None, reference_doctype=None,
	sender=None, cc=None , attachments=None, delay=None, args=None, template=None):
	logo = "https://one-fm.com/files/ONEFM_Identity.png"

	if not message:
		message = " "

	if "Administrator" in recipients:
		recipients.remove("Administrator")
	
	if args:
		extra_message, text_content = get_email_from_template("default_email", args)
		if extra_message:
			message += extra_message

	if attachments:
		message += """
			<p>Please find the attached Document in the mail below.</p>
		"""

	for recipient in recipients:
		if is_user_id_not_company_prefred_email_in_employee(recipient):
			recipients.remove(recipient)

	if recipients and len(recipients) > 0:
		frappe.sendmail(template = "default_email",
			recipients=recipients,
			sender= sender,
			cc=cc,
			reference_name= reference_name,
			reference_doctype = reference_doctype,
			subject=subject,
			args=dict(
				header=header[0] if header else "",
				subject=subject,
				message=message,
				content=content,
				logo=logo
			),
			attachments = attachments,
			delayed=delay
		)

def is_user_id_not_company_prefred_email_in_employee(user_id):
	'''
		This method is used for finding the receiver is company prefered_email
		in the employee record linked with the user_id
		args:
			user_id: email id (Text)(Email)
		return True if user id is not company prefered email id
		return False if employee not exists for the user id / user id is company prefered email id
	'''
	user_id_not_company_prefred_in_employee = False
	employee = frappe.db.exists('Employee', {'user_id': user_id})
	if employee:
		user_id_not_company_prefred_in_employee = True
		prefered_email, company_email, prefered_contact_email = frappe.db.get_value("Employee", employee, ["prefered_email", "company_email", "prefered_contact_email"])
		if prefered_contact_email == 'Company Email' and prefered_email == company_email and prefered_email == user_id:
			user_id_not_company_prefred_in_employee = False
	return user_id_not_company_prefred_in_employee

@frappe.whitelist()
def send_whatsapp(sender_id, body):
	twilio = frappe.get_doc('Twilio Setting' )

	client =  TwilioClient(twilio.sid, twilio.token)

	message = client.messages.create(
		from_='whatsapp:' + twilio.t_number,
		body=body,
		to= 'whatsapp:+'+ sender_id
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
