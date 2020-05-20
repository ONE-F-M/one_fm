# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class JobApplicantInterviewSheet(Document):
	def validate(self):
		calculate_average_score(self)

def calculate_average_score(doc):
	sections = ['General', 'Attitude', 'Technical', 'Experience', 'Language']
	for section in sections:
		table = doc.get('interview_sheet_'+section.lower())
		if table:
			table_row_count = 0
			total_table_score = 0
			for item in table:
				table_row_count += 1
				total_table_score += item.score if item.score else 0
			average_score = 0
			if table_row_count and total_table_score:
				average_score = total_table_score/table_row_count
			doc.set(section.lower()+'_average_score', average_score)

@frappe.whitelist()
def get_interview_template_details(template_name):
	template = frappe.get_doc('Interview', template_name)
	template_list = {}
	if template and template.for_interview_sheet:
		if template.general:
			template_list['General'] = frappe.get_doc('Interview', template.general)
		if template.attitude:
			template_list['Attitude'] = frappe.get_doc('Interview', template.attitude)
		if template.technical:
			template_list['Technical'] = frappe.get_doc('Interview', template.technical)
		if template.work_experience:
			template_list['Work Experience'] = frappe.get_doc('Interview', template.work_experience)
		if template.language:
			template_list['Language'] = frappe.get_doc('Interview', template.language)
	return template_list
