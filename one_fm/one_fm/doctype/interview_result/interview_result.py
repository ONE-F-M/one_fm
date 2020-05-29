# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from one_fm.utils import validate_applicant_overseas_transferable
from frappe import _

class InterviewResult(Document):
	def validate(self):
		self.validate_with_applicant()
		self.calculate_total_and_avg_score()

	def before_submit(self):
		self.average_score_action()

	def average_score_action(self):
		if self.average_score < 2.99:
			if not self.pass_to_next_interview:
				frappe.throw(_("Score is less than 2.99, Please Select Pass to Next Interview or Reject Applicant"))

	def calculate_total_and_avg_score(self):
		total = 0
		no_of_questions = 0
		avg = 0
		if self.is_bulk:
			interview_tables = ['interview_sheet_general', 'interview_sheet_attitude', 'interview_sheet_technical']
			for interview_table in interview_tables:
				interview_questions = self.get(interview_table)
				if interview_questions:
					for interview_question in interview_questions:
						total += interview_question.score
					no_of_questions += len(interview_questions)
			total += self.work_experience_score if self.work_experience_score else 0
			no_of_questions += 1

		elif self.interview_question_result:
			for interview_question in self.interview_question_result:
				total += interview_question.score
			no_of_questions += len(self.interview_question_result)
		self.total_score = total

		if total and no_of_questions > 0:
			avg = total/no_of_questions
		self.average_score = avg

	def on_submit(self):
		create_best_reference(self)
		update_interview_score_of_applicant(self)

	def on_cancel(self):
		remove_best_reference(self)
		update_interview_score_of_applicant(self, True)

	def validate_with_applicant(self):
		if self.job_applicant:
			if frappe.db.get_value('Job Applicant', self.job_applicant, 'status') == 'Rejected':
				frappe.throw(_('Applicant is Rejected'))
			validate_applicant_overseas_transferable(self.job_applicant)

def update_interview_score_of_applicant(doc, cancel=False):
	if cancel:
		score = frappe.db.exists('Job Applicant Score', {'parent': doc.job_applicant, 'reference_dt': doc.doctype, 'reference_dn': doc.name})
		if score:
			frappe.delete_doc('Job Applicant Score', score)
			if doc.average_score < 2.99 and doc.pass_to_next_interview == "Reject":
				frappe.db.set_value('Job Applicant', doc.job_applicant, 'status', 'Open')
	else:
		job_applicant = frappe.get_doc('Job Applicant', doc.job_applicant)
		interview_score = job_applicant.append('one_fm_job_applicant_score')
		interview_score.interview = doc.interview_template
		interview_score.score = doc.average_score
		interview_score.reference_dt = doc.doctype
		interview_score.reference_dn = doc.name
		interview_score.date = getdate(doc.interview_date)
		if doc.average_score < 2.99 and doc.pass_to_next_interview == "Reject":
			job_applicant.status = 'Rejected'
		job_applicant.save(ignore_permissions=True)

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
