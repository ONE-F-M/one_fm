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
		data = frappe.request.data
		# tree = ET.fromstring(data)
		# body = tree.find('Body').text
		# from_ = tree.find('From').text.split('+')[1]
		message = "Hello, the data is " + data.decode("utf-8") 
		res = send_whatsapp(sender_id="96590042238", body=message)
	else:
		possibility = "False"
	# message = request.form['Body']
	# senderId = request.form['From'].split('+')[1]

	return '200'