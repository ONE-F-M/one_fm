# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class InterviewResult(Document):
	def on_submit(self):
		create_best_reference(self)

	def on_cancel(self):
		remove_best_reference(self)

def remove_best_reference(doc):
	references = frappe.get_list('Best Reference', {'interview': doc.name})
	for reference in references:
		frappe.delete_doc('Best Reference', reference.name)

def create_best_reference(doc):
	if doc.get_best_reference and doc.best_references:
		for ref in doc.best_references:
			reference = frappe.new_doc('Best Reference')
			reference.reference = ref.reference
			reference.name_of_person = ref.name_of_person
			reference.contact_number = ref.contact_number
			reference.email = ref.email
			reference.why_he = ref.why_he
			reference.reference_feedback = ref.reference_feedback
			reference.interview = doc.name
			reference.job_applicant = doc.job_applicant
			country_code, contact_number = frappe.db.get_value('Job Applicant', doc.job_applicant, ['one_fm_country_code_country', 'one_fm_contact_number'])
			reference.applicant_contact_number = ((country_code+' ') if country_code else '')+contact_number
			reference.designation = ref.designation
			reference.save(ignore_permissions=True)
