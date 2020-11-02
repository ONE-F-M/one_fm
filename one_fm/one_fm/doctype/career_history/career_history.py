# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate
from one_fm.utils import validate_applicant_overseas_transferable

class OverlapError(frappe.ValidationError): pass
class CareerHistory(Document):
	def on_update(self):
		update_career_history_score_of_applicant(self)

	def validate(self):
		self.validate_with_applicant()
		self.validate_dates()
		set_totals_in_career_history_company(self)
		self.validate_date_overlap_within_childs()
		self.validate_pormotions_and_salary_during_company()
		self.validate_pormotions_exist_for_company()
		self.validate_salary_hikes_exist_for_company()
		self.calculate_career_history_score()
		self.career_history_score_action()

	def career_history_score_action(self):
		if self.career_history_score and self.career_history_score > 0 and self.career_history_score < 2.99:
			if not self.pass_to_next_interview:
				frappe.throw(_("Score is less than 2.99, Please Select Pass to Next Interview or Reject Applicant"))

	def calculate_career_history_score(self):
		career_history_score = 0;
		if self.number_promotions_and_salary_changes and self.total_years_of_experience:
			the_factor = self.number_promotions_and_salary_changes/self.total_years_of_experience
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

	def validate_salary_hikes_exist_for_company(self):
		for company in self.career_history_company:
			if company.did_you_get_any_salary_increase == 'Yes':
				hikes_for_company = False
				if self.salary_hikes:
					for salary_hike in self.salary_hikes:
						if company.company_name == salary_hike.company_name:
							hikes_for_company = True
				if not hikes_for_company:
					frappe.throw(_('You have to add Salary Hikes for the Company {0}').format(company.company_name))

	def validate_pormotions_exist_for_company(self):
		for company in self.career_history_company:
			if company.did_you_get_any_promotion == 'Yes':
				promotions_for_company = False
				if self.promotions:
					for promotion in self.promotions:
						if company.company_name == promotion.company_name:
							promotions_for_company = True
				if not promotions_for_company:
					frappe.throw(_('You have to add Promotions for the Company {0}').format(company.company_name))

	def validate_pormotions_and_salary_during_company(self):
		for company in self.career_history_company:
			if self.promotions:
				for promotion in self.promotions:
					if company.company_name == promotion.company_name:
						if promotion.start_date < company.job_start_date or promotion.end_date > company.job_end_date:
							frappe.throw(_("Row {0}: Start Date and End Date of Promotion not during the ({1}) days")
								.format(promotion.idx, promotion.company_name), OverlapError)
			if self.salary_hikes:
				for salary_hike in self.salary_hikes:
					if company.company_name == salary_hike.company_name:
						if salary_hike.start_date < company.job_start_date or salary_hike.end_date > company.job_end_date:
							frappe.throw(_("Row {0}: Start Date and End Date of Salary Hike not during the ({1}) days")
								.format(salary_hike.idx, salary_hike.company_name), OverlapError)

	def validate_date_overlap_within_childs(self):
		for company in self.career_history_company:
			validate_overlap(self, company, 'Company')
		if self.promotions:
			for promotion in self.promotions:
				validate_overlap(self, promotion, 'Promotions')

		if self.salary_hikes:
			for salary_hike in self.salary_hikes:
				validate_overlap(self, salary_hike, 'Salary Hikes')

	def validate_dates(self):
		self.validate_dates_in_child('career_history_company', 'job_start_date', 'job_end_date', 'Career History')
		self.validate_dates_in_child('promotions', 'start_date', 'end_date', 'Promotions')
		self.validate_dates_in_child('salary_hikes', 'start_date', 'end_date', 'Salary Hikes')


	def validate_dates_in_child(self, child_name, start_date_field, end_date_field, table_label):
		for child in self.get(child_name):
			if child.get(start_date_field) > child.get(end_date_field):
				frappe.throw(_("Row {0}: End Date cannot be before Start Date in {1}")
					.format(child.idx, table_label), OverlapError)

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

def validate_overlap(doc, child_doc, table):
	query = """
		select
			name
		from
			`tab{0}`
		where
			name != %(name)s and parent = %(parent)s
		"""
	query += get_doc_condition(table)

	if not child_doc.name:
		# hack! if name is null, it could cause problems with !=
		child_doc.name = "New "+child_doc.doctype

	query_filter = {"name": child_doc.name, "parent": doc.name}
	if table == 'Company':
		query_filter['start_date'] = child_doc.job_start_date
		query_filter['end_date'] = child_doc.job_end_date
	else:
		query_filter['start_date'] = child_doc.start_date
		query_filter['end_date'] = child_doc.end_date
		query_filter['company_name'] = child_doc.company_name

	overlap_doc = frappe.db.sql(query.format(child_doc.doctype), query_filter, as_dict = 1)

	if overlap_doc:
		frappe.throw(_("Row {0}: Start Date and End Date of Career History ({1}) is overlapping with {2}")
			.format(child_doc.idx, table, overlap_doc[0].company), OverlapError)

def get_doc_condition(table):
	if table == 'Company':
		return """
			and (job_start_date between %(start_date)s and %(end_date)s
			or job_end_date between %(start_date)s and %(end_date)s
			or (job_start_date < %(start_date)s and job_end_date > %(end_date)s))
		"""
	return """
		and company_name = %(company_name)s and (start_date between %(start_date)s and %(end_date)s
		or end_date between %(start_date)s and %(end_date)s
		or (start_date < %(start_date)s and end_date > %(end_date)s))
	"""

def set_totals_in_career_history_company(doc):
	if doc.career_history_company:
		for company in doc.career_history_company:
			total_promotion = 0
			total_salary_hike = 0
			recruiter_validation_score_promotion = 0
			recruiter_validation_score_salary_change = 0
			if doc.promotions:
				for promotion in doc.promotions:
					if company.company_name == promotion.company_name:
						total_promotion += 1
						if promotion.recruiter_validation_score:
							recruiter_validation_score_promotion += promotion.recruiter_validation_score
			if doc.salary_hikes:
				for salary_hike in doc.salary_hikes:
					if company.company_name == salary_hike.company_name:
						total_salary_hike += 1
						if salary_hike.recruiter_validation_score:
							recruiter_validation_score_salary_change += salary_hike.recruiter_validation_score
			company.total_promotions = total_promotion
			company.recruiter_validation_score_promotion = recruiter_validation_score_promotion
			company.total_salary_changes = total_salary_hike
			company.recruiter_validation_score_salary_change = recruiter_validation_score_salary_change

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
						<td><b>Years of Experience</b></td>
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
								{{ item.years_of_experience_str }}
							</td>
						</tr>
					{% endfor %}
				</tbody>
			</table>
		</div>
		{% endif %}
	"""
