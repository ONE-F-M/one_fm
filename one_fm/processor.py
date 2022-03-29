import frappe
import requests
import json
from twilio.rest import Client as TwilioClient
import xml.etree.ElementTree as ET


@frappe.whitelist()
def sendemail(recipients, subject, header=None, message=None,
        content=None, reference_name=None, reference_doctype=None,
        sender=None, cc=None , attachments=None, delay=None):
    logo = "https://one-fm.com/files/ONEFM_Identity.png"

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
                    delayed=delay)

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
