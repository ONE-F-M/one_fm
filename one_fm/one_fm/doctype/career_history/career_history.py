# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, month_diff
from one_fm.utils import validate_applicant_overseas_transferable

class OverlapError(frappe.ValidationError): pass
class CareerHistory(Document):
	def on_update(self):
		update_career_history_score_of_applicant(self)

	def validate(self):
		self.validate_with_applicant()
		self.calculate_promotions_and_experience()
		self.calculate_career_history_score()
		self.career_history_score_action()
		for company in self.career_history_company:
			# Validate Overlaping of Career History Company Details with Date
			validate_overlap(self, company)

	def career_history_score_action(self):
		if self.career_history_score and self.career_history_score > 0 and self.career_history_score < 2.99:
			if not self.pass_to_next_interview:
				frappe.throw(_("Score is less than 2.99, Please Select Pass to Next Interview or Reject Applicant"))

	def calculate_career_history_score(self):
		career_history_score = 0;
		if self.total_number_of_promotions_and_salary_changes and self.total_years_of_experience:
			the_factor = self.total_number_of_promotions_and_salary_changes/self.total_years_of_experience
			if the_factor >= 0 and the_factor < 0.25:
				career_history_score = 1
			elif the_factor >= 0.25 and the_factor < 0.33:
				career_history_score = 2
			elif the_factor >= 0.33 and the_factor < 0.5:
				career_history_score = 3
			elif the_factor >= 0.5 and the_factor < 1:
				career_history_score = 4
			elif the_factor >= 1:
				career_history_score = 5
		self.career_history_score = career_history_score
		if career_history_score <= 0 and self.pass_to_next_interview:
			self.pass_to_next_interview = ''

	def validate_with_applicant(self):
		if self.job_applicant:
			if frappe.db.get_value('Job Applicant', self.job_applicant, 'status') == 'Rejected':
				frappe.throw(_('Applicant is Rejected'))
			validate_applicant_overseas_transferable(self.job_applicant)
		if not self.name:
			# hack! if name is null, it could cause problems with !=
			self.name = "New "+self.doctype
		career_history = frappe.db.exists('Career History', {'job_applicant': self.job_applicant, 'name': ['!=', self.name]})
		if career_history:
			frappe.throw(_("""Career History <b><a href="#Form/Career History/{0}">{0}</a></b> is exists against \
				Job Applicant {1}.!""").format(career_history, self.applicant_name))

	def on_trash(self):
		update_career_history_score_of_applicant(self, True)

	def calculate_promotions_and_experience(self):
		'''
			Method to calculate and set Promotion and Experience
			args: self: Career History Object
		'''
		total_number_of_promotions = 0
		total_number_of_salary_changes = 0
		total_months_of_experience = 0
		if self.career_history_company:
			start_date_in_company = {}
			promotions = {}
			salary_hikes = {}
			end_date_in_company = {}
			for item in self.career_history_company:
				if item.company_name not in start_date_in_company:
					start_date_in_company[item.company_name] = item.start_date
				if item.company_name not in end_date_in_company and item.end_date:
					end_date_in_company[item.company_name] = item.end_date
				if item.company_name not in promotions:
					promotions[item.company_name] = [item.job_title]
				elif promotions[item.company_name] != item.job_title:
					promotions[item.company_name].append(item.job_title)
				if item.company_name not in salary_hikes:
					salary_hikes[item.company_name] = [item.monthly_salary_in_kwd]
				elif salary_hikes[item.company_name] != item.monthly_salary_in_kwd:
					salary_hikes[item.company_name].append(item.monthly_salary_in_kwd)

		for company in start_date_in_company:
			start_date = start_date_in_company[company]
			if company in end_date_in_company:
				total_months_of_experience += month_diff(getdate(end_date_in_company[company]), getdate(start_date))-1
			if company in promotions:
				total_number_of_promotions += len(promotions[company])-1
			if company in salary_hikes:
				total_number_of_salary_changes += len(salary_hikes[company])-1
		self.total_number_of_promotions_and_salary_changes = total_number_of_promotions+total_number_of_salary_changes
		if total_months_of_experience:
			self.total_years_of_experience = total_months_of_experience/12

def update_career_history_score_of_applicant(doc, delete=False):
	job_applicant = frappe.get_doc('Job Applicant', doc.job_applicant)
	career_history_score_exists = False
	if job_applicant.one_fm_job_applicant_score:
		for score in job_applicant.one_fm_job_applicant_score:
			if score.reference_dt == doc.doctype and score.reference_dn == doc.name:
				career_history_score_exists = True
				if delete:
					frappe.delete_doc('Job Applicant Score', score.name)
				else:
					score.score = doc.career_history_score if doc.career_history_score else 0
					score.date = getdate(doc.validated_by_recruiter_on)
	if not career_history_score_exists:
		interview_score = job_applicant.append('one_fm_job_applicant_score')
		interview_score.interview = 'Career History'
		interview_score.score = doc.career_history_score if doc.career_history_score else 0
		interview_score.reference_dt = doc.doctype
		interview_score.reference_dn = doc.name
		interview_score.date = getdate(doc.validated_by_recruiter_on)
	if doc.pass_to_next_interview == "Reject" and doc.career_history_score and doc.career_history_score > 0 and doc.career_history_score < 2.99:
		job_applicant.status = 'Rejected' if not delete else 'Open'
	job_applicant.save(ignore_permissions=True)

def validate_overlap(doc, child_doc):
	'''
		Method used Validate Overlaping of Career History Company Details with Date
		args:
			doc: Object of Career History
			child_doc: Object of Career History Company
	'''

	query = """
		select
			name
		from
			`tab{0}`
		where
			name != %(name)s and parent = %(parent)s
			and (start_date between %(start_date)s and %(end_date)s
			or end_date between %(start_date)s and %(end_date)s
			or (start_date < %(start_date)s and end_date > %(end_date)s))
		"""

	if not child_doc.name:
		# hack! if name is null, it could cause problems with !=
		child_doc.name = "New "+child_doc.doctype

	query_filter = {"name": child_doc.name, "parent": doc.name, "start_date": child_doc.start_date, "end_date": child_doc.end_date}

	overlap_doc = frappe.db.sql(query.format(child_doc.doctype), query_filter, as_dict = 1)

	if overlap_doc:
		frappe.throw(_("Row {0}: Start Date and End Date in Career History Company is overlapping with {1}")
			.format(child_doc.idx, overlap_doc[0].idx), OverlapError)

@frappe.whitelist()
def get_career_history(job_applicant):
	career_history_id = frappe.db.exists('Career History', {'job_applicant': job_applicant})
	if career_history_id:
		return frappe.get_doc('Career History', career_history_id)
	return None

@frappe.whitelist()
def get_career_history_as_html(job_applicant):
	career_history = get_career_history(job_applicant)
	return career_history_html(career_history) if career_history else ''

def career_history_html(career_history):
	if career_history.career_history_company:
		template = get_career_history_html_template()
		return frappe.render_template(
			template, dict(objectives=career_history.career_history_company)
		)

def get_career_history_html_template():
	return """
		{% if objectives %}
		<div>
			<b><u>Experience Details:</u></b>
		</div>
		<div style="overflow-x: auto;">
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<td><b>Company Name</b></td>
						<td><b>Job Title</b></td>
						<td><b>Country of Experience</b></td>
						<td><b>Start Date</b></td>
						<td><b>End Date</b></td>
					</tr>
				</thead>
				<tbody>
					{% for item in objectives %}
						<tr>
							<td>{{ item.company_name }}</td>
							<td>
								{{ item.job_title }}
							</td>
							<td>
								{{ item.country_of_employment }}
							</td>
							<td>
								{{ item.start_date }}
							</td>
							<td>
								{{ item.end_date }}
							</td>
						</tr>
					{% endfor %}
				</tbody>
			</table>
		</div>
		{% endif %}
	"""
