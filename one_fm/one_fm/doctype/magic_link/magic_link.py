# Copyright (c) 2021, one fm and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import decrypt, encrypt
from frappe.utils import get_url
from one_fm.processor import sendemail

class MagicLink(Document):
	pass

def get_encrypted_magic_link(magic_link):
	'''
		Method is used to encrypt the magic link
		args:
			magic_link: Magic Link ID (example: ML.0000001)
		return encrypted magic link id
	'''
	return encrypt(magic_link)

def get_magic_link(doctype, name, link_for):
	'''
		Method used to send the magic Link to the Job Applicant from Job Applicant doctype
		args:
			doctype: Reference Doctype name, from which the magic link created
			name: Reference Doctype ID, from which the magic link created
			link_for: The doctype for which the magic link is created (example: Career History)

		return Magic Link ID
	'''

	# Check if magic_link exists for the given doctype and not expired

	magic_link = frappe.db.exists('Magic Link',
		{'reference_doctype': doctype, 'reference_docname': name, 'expired': False, 'link_for': link_for})

	# If there is no magic link exist for the reference, then create a magic link
	if not magic_link:
		magic_link = create_magic_link(doctype, name, link_for)

	return magic_link

def create_magic_link(doctype, name, link_for):
	'''
		Method used to send the magic Link to the Job Applicant from Job Applicant doctype
		args:
			doctype: Reference Doctype name, from which the magic link created
			name: Reference Doctype ID, from which the magic link created
			link_for: The doctype for which the magic link is created (example: Career History)

		return Magic Link ID
	'''
	magic_link = frappe.new_doc('Magic Link')
	magic_link.reference_doctype = doctype
	magic_link.reference_docname = name
	magic_link.link_for = link_for
	magic_link.save(ignore_permissions=True)
	return magic_link.name

def authorize_magic_link(encrypted_magic_link, doctype, link_for):
	'''
		Method is used to check the magic ling exist or expired
		args:
			encrypted_magic_link: encrypted value of Magic Link ID
			doctype: Reference Doctype name, from which the magic link created
			link_for: The doctype for which the magic link is created (example: Career History)

		return Magic Link ID (example: ML.000001)
	'''
	# Set decrypted_magic_link as false to initialize
	decrypted_magic_link = False
	try:
		'''
			Set decrypted_magic_link as the decripted value (example: ML.000001, the magic link ID)
			If the encrypted_magic_link is dirty then decrypt method will raise an exceptions
		'''
		decrypted_magic_link = decrypt(encrypted_magic_link)
	except Exception as e:
		frappe.log_error(str(encrypted_magic_link), 'Dirty Magic Link')
		frappe.throw(_("Sorry, we could not able to decrypt the magic link"), frappe.PermissionError)

	if decrypted_magic_link:
		magic_link_exists = frappe.db.exists('Magic Link', {'name': decrypted_magic_link})
		if magic_link_exists:
			magic_link_expired = frappe.db.get_value('Magic Link', magic_link_exists, 'expired')
			if magic_link_expired:
				frappe.log_error(str(decrypted_magic_link), 'Magic Link expired')
				frappe.throw(_("Sorry, the given link is expired!"), frappe.PermissionError)
			return magic_link_exists
		else:
			frappe.log_error(str(decrypted_magic_link), 'Magic Link Not exist')
			frappe.throw(_("Sorry, we could not find what you're looking for :/"), frappe.PermissionError)

def send_magic_link(doctype, name, link_for, recipients, url_prefix, msg, subject):
	'''
	Method used to send the magic Link for link_for doctype to the doctype
	args:
		doctype: Reference Doctype name, from which the magic link created
		name: Reference Doctype ID, from which the magic link created
		link_for: The doctype for which the magic link is created (example: Career History)
		recipients: array of recipient email(s) (example: [jam@one-fm.com])
		url_prefix: prefix to the url (example: "/career_history?magic_link=")
		msg: Message content to the Recipients without the magic link
		subject: Subject of the email
	'''
	# Check if magic_link exists for the Job Applicant and not expired
	magic_link = get_magic_link(doctype, name, link_for)
	if magic_link:
		# Encrypt the magic link benfore send
		encrypted_magic_link = get_encrypted_magic_link(magic_link)
		# Email Magic Link to the Recipients
		sender = frappe.get_value("Email Account", filters={"default_outgoing": 1}, fieldname="email_id") or None
		magic_link_url = get_url(url_prefix) + encrypted_magic_link
		msg += "<br/><a class='btn btn-primary' href='{0}'>Magic Link</a>".format(magic_link_url)
		frappe.enqueue(sendemail, sender=sender, recipients=recipients, content=msg, subject=subject, is_external_mail=True)
		frappe.msgprint(("Email has been sent to the {0} with the magic link <br/><b><a href='{1}' target='_blank'>Click here to see the magic link for {2}</a></b>".format(doctype, magic_link_url, link_for)), alert=True)
		if link_for == "Career History":
			frappe.db.set_value(doctype, name, 'career_history_ml', magic_link)
			frappe.db.set_value(doctype, name, 'career_history_ml_url', magic_link_url)
			frappe.db.set_value(doctype, name, 'career_history_ml_expired', False)

		if link_for == "Job Applicant":
			frappe.db.set_value(doctype, name, 'applicant_doc_ml', magic_link)
			frappe.db.set_value(doctype, name, 'applicant_doc_ml_url', magic_link_url)
			frappe.db.set_value(doctype, name, 'applicant_doc_ml_expired', False)
