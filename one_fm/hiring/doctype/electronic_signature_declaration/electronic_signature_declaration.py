# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model import core_doctypes_list
from frappe.model.document import Document
from frappe.utils import cstr
from one_fm.hiring.utils import update_onboarding_doc_workflow_sate

class ElectronicSignatureDeclaration(Document):
	def after_insert(self):
		self.update_onboarding_doc()
		update_onboarding_doc_workflow_sate(self)

	def update_onboarding_doc(self, cancel=False):
		if self.onboard_employee:
			onboard_employee = frappe.get_doc('Onboard Employee', self.onboard_employee)
			if cancel:
				onboard_employee.declaration_of_electronic_signature = ''
			else:
				onboard_employee.declaration_of_electronic_signature = self.name
			onboard_employee.save(ignore_permissions=True)
