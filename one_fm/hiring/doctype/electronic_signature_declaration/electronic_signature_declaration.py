# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model import core_doctypes_list
from frappe.model.document import Document
from frappe.utils import cstr

class ElectronicSignatureDeclaration(Document):
	pass

@frappe.whitelist()
def get_signature_status(declaration_of_electronic_signature):
	signature = frappe.get_value("Electronic Signature Declaration", declaration_of_electronic_signature, ['applicant_signature'])
	if signature:
		return 1
	else:
		return 0
