# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model import core_doctypes_list
from frappe.model.document import Document
from frappe.utils import cstr

class frappe.get_value("Electronic Signature Declaration", declaration_of_electronic_signature, ['applicant_signature'])(Document):
	pass

@frappe.whitelist()
def check_signature_status(declaration_of_electronic_signature):
	"""This function is to check if the signature exist in the Electronic Signature Declaration doctype

	Args:
		declaration_of_electronic_signature ([doctype]): doc ID

	Returns:
		1: [if signature exist]
		0: [if signature doesn't exist]
	"""
	if frappe.get_value("Electronic Signature Declaration", declaration_of_electronic_signature, ['applicant_signature']):
		return 1
	else:
		return 0
