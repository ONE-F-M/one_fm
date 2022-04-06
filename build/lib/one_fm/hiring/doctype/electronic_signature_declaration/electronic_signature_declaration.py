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
		self.update_employee_detail()
		self.update_declaration_statement()
		update_onboarding_doc_workflow_sate(self)

	def on_update_after_submit(self):
		if self.new_employee == 0:
			self.update_employee_doc()
		else:
			self.update_onboarding_doc()
	
	def update_employee_detail(self):
		#fetch employee details fron onboarding if employee is new.
		if self.new_employee == 1 and self.onboard_employee:
			onboard_employee_doc = frappe.get_all("Onboard Employee",{"name":self.onboard_employee},["*"])
			self.employee_name = onboard_employee_doc[0].employee_name
			self.employee_name_in_arabic = onboard_employee_doc[0].employee_name_in_arabic
			self.nationality = onboard_employee_doc[0].nationality
			self.civil_id = onboard_employee_doc[0].civil_id
			self.company = onboard_employee_doc[0].company
			self.save(ignore_permissions=True)

	def update_onboarding_doc(self, cancel=False):
		# if new employee and onboad employee doc exist, update the onboard employee doc.
		if self.onboard_employee:
			onboard_employee = frappe.get_doc('Onboard Employee', self.onboard_employee)
			if cancel:
				onboard_employee.declaration_of_electronic_signature = ''
				onboard_employee.electronic_signature_status = False
			else:
				if self.applicant_signature:
					onboard_employee.electronic_signature_status = True
				onboard_employee.declaration_of_electronic_signature = self.name
			onboard_employee.save(ignore_permissions=True)

	def update_declaration_statement(self):
		# for existiong employee, create Declaration statement in English and Arabic.
		if self.employee_name:
			self.declarationen = "<h4>I,  {0}, nationality  {1}, holding civil ID no. {2} the undersigned, acknowledge that the signature written at the bottom of this acknowledgment is my own, certified, and valid signature, and that I acknowledge the acceptance and enforcement of this signature against me and against others, and I authorize {3} company / to adopt this signature as a legally valid electronic signature.</h4>".format(self.employee_name,self.nationality,self.civil_id,self.company)
			self.declarationar = "<h4>{0} قر أنا الموقع أدناه  / ، واحمل بطاقة مدنية ر {1} الجنسية({2}) بأن التوقيع المدون أسفل هذا اإلقرار و التوقيع الخاص بي معتمد وساري ،وأنني اقر بقبول ونفاذ هذا التوقيع في مواجهتي مواجهة الغير ، باعتماد {3}وأنني افوض شركة / .هذا التوقيع كتوقيع إلكتروني ساري المفعول قانوناً</h4>".format(self.employee_name_in_arabic,frappe.db.get_value("Nationality", self.nationality, 'nationality_arabic'),self.civil_id,self.company)
			self.save()

	def update_employee_doc(self):
		#on update, if employee already exist, update employee document with signature.
		if self.employee and self.applicant_signature:
			employee_doc = frappe.get_doc("Employee",self.employee)
			employee_doc.employee_signature = self.applicant_signature
			employee_doc.save(ignore_permissions=True)
			frappe.db.commit()