# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, month_diff, today, now, get_link_to_form
from one_fm.utils import validate_applicant_overseas_transferable

class OverlapError(frappe.ValidationError): pass
class CareerHistory(Document):
	def on_update(self):
		update_interview_and_feedback(self)

	def validate(self):
		self.validate_with_applicant()
		if self.career_history_company and self.calculate_promotions_and_experience_automatically:
			self.calculate_promotions_and_experience()
		self.calculate_career_history_score()
		self.career_history_score_action()

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
			# validate_applicant_overseas_transferable(self.job_applicant)
		if not self.name:
			# hack! if name is null, it could cause problems with !=
			self.name = "New "+self.doctype
		career_history = frappe.db.exists('Career History', {'job_applicant': self.job_applicant, 'name': ['!=', self.name]})
		if career_history:
			frappe.throw(_("""Career History <b><a href="#Form/Career History/{0}">{0}</a></b> is exists against \
				Job Applicant {1}.!""").format(career_history, self.applicant_name))

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

	def	on_submit(self):
		update_interview_and_feedback(self, True)

	def on_cancel(self):
		cancel_interview_and_feedback(self)

def cancel_interview_and_feedback(career_history):
	interview_feedback_exists = frappe.db.exists('Interview Feedback',
		{'career_history': career_history.name, 'docstatus': ['>', 1]})
	if interview_feedback_exists:
		interview = frappe.get_value('Interview Feedback', interview_feedback_exists, 'interview')
		if interview and frappe.get_value('Interview Detail', filters={'parent': interview, 'interviewer': frappe.session.user}):
			frappe.get_doc('Interview', interview).cancel()

def update_interview_and_feedback(career_history, submit=False):
	"""
		Method is used to create or update interview and interview feedback
		args:
			career_history: Object of career_history
	"""
	interview_feedback_exists = frappe.db.exists('Interview Feedback',
		{'career_history': career_history.name, 'docstatus': 0})
	if interview_feedback_exists:
		interview_feedback = frappe.get_doc('Interview Feedback', interview_feedback_exists)
	else:
		interview_feedback = frappe.new_doc('Interview Feedback')
	interview_feedback.interview = get_interview(career_history)
	interview_feedback.interviewer = frappe.session.user
	interview_feedback.job_applicant = career_history.job_applicant
	interview_feedback.career_history = career_history.name
	interview_feedback.skill_assessment = []
	interview_feedback.append('skill_assessment', {'skill': 'Career History', 'rating': career_history.career_history_score})
	from frappe.website.utils import get_comment_list
	comment_list = get_comment_list('Career History', career_history.name)
	if comment_list and len(comment_list) > 0:
		from frappe.utils.html_utils import clean_html
		interview_feedback.feedback = clean_html(comment_list[0].content)
	interview_feedback.result = get_career_history_result(career_history)
	interview_feedback.save(ignore_permissions=True)

	if submit:
		interview_feedback.submit()
		interview = frappe.get_doc('Interview', interview_feedback.interview)
		interview.status = interview_feedback.result
		interview.submit()

	frappe.msgprint(_('Interview Feedback {0} {1} successfully').format(
		get_link_to_form('Interview Feedback', interview_feedback.name), 'submitted' if submit else 'saved'))

def get_interview(career_history):
	interview_exists = frappe.db.exists('Interview',
		{'career_history': career_history.name, 'docstatus': ['!=', 2]})
	if interview_exists:
		from erpnext.hr.doctype.interview_feedback.interview_feedback import get_applicable_interviewers
		applicable_interviewers = get_applicable_interviewers(interview_exists)
		if frappe.session.user in applicable_interviewers:
			return interview_exists
	return create_interview(career_history)

def create_interview(career_history):
		interview = frappe.new_doc('Interview')
		interview.interview_round = 'Career History'
		interview.job_applicant = career_history.job_applicant
		interview.career_history = career_history.name
		interview.scheduled_on = today()
		interview.from_time = now()
		interview.to_time = now()
		interview_details = interview.append('interview_details')
		interview_details.interviewer = frappe.session.user
		interview.expected_average_rating = 5
		interview.save(ignore_permissions = True)
		return interview.name

def get_career_history_result(career_history):
	if career_history.career_history_score < 2.99 and career_history.pass_to_next_interview == 'Rejected':
		return 'Rejected'
	return 'Cleared'

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
