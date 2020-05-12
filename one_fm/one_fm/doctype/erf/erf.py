# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe import _

class ERF(Document):
	def validate(self):
		self.set_erf_code()
		self.validate_date()
		self.validate_languages()
		self.set_other_benefits()
		self.validate_type_of_license()
		self.set_salary_structure_from_grade()
		self.set_salary_details()
		self.calculate_total_required_candidates()
		self.calculate_salary_per_person()
		self.calculate_total_cost_in_salary()
		self.calculate_benefit_cost_to_company()
		self.calculate_total_cost_to_company()
		self.validate_with_erf_request()
		self.validate_type_of_travel()

	def validate_date(self):
		if self.erf_initiation > self.expected_date_of_deployment:
			frappe.throw(_("Expected Date of Deployment cannot be before ERF Initiation Date"))
		if self.expected_date_of_deployment < today():
			frappe.throw(_("Expected Date of Deployment cannot be before Today"))

	def on_submit(self):
		self.set_erf_request()
		self.set_erf_finalized()
		self.validate_recruiter_assigned()
		if self.status == 'Draft':
			frappe.throw(_('You can not Submit ERF with Draft Status.'))
		if self.status == 'Accepted':
			create_job_opening_from_erf(self)
		frappe.msgprint(_('Department Manager Will Notified By Email.'))

	def set_erf_request(self):
		frappe.db.set_value('ERF Request', self.erf_request, 'erf_created', True)

	def set_erf_code(self):
		self.erf_code = self.name

	def set_erf_finalized(self):
		self.erf_finalized = today()

	def validate_languages(self):
		if self.languages:
			for language in self.languages:
				if not language.read and not language.write and not language.speak:
					frappe.throw(_("Select Language for Speak, Read or Write.!"))

	def validate_type_of_travel(self):
		if self.travel_required and not self.type_of_travel:
			frappe.throw(_('Type of Travel is Mandatory Field.!'))

	def validate_type_of_license(self):
		if self.driving_license_required and not self.type_of_license:
			frappe.throw(_('Type of License is Mandatory Field.!'))

	def set_salary_structure_from_grade(self):
		if self.grade and not self.salary_structure and not self.salary_details:
			self.salary_structure = frappe.db.get_value('Employee Grade', self.grade, 'default_salary_structure')

	def set_salary_details(self):
		if self.salary_structure and not self.salary_details:
			salary_structure = frappe.get_doc('Salary Structure', self.salary_structure)
			if salary_structure.earnings:
				for earning in salary_structure.earnings:
					salary_detail = self.append('salary_details')
					salary_detail.salary_component = earning.salary_component
					salary_detail.amount = earning.amount

	def calculate_total_required_candidates(self):
		total = 0
		if self.gender_height_requirement:
			for required_candidate in self.gender_height_requirement:
				total += required_candidate.number
		self.total_no_of_candidates_required = total

	def calculate_salary_per_person(self):
		total = 0
		if self.salary_details:
			for salary_detail in self.salary_details:
				total += salary_detail.amount if salary_detail.amount else 0
		self.salary_per_person = total

	def calculate_total_cost_in_salary(self):
		if self.total_no_of_candidates_required > 0 and self.salary_per_person > 0:
			self.total_cost_in_salary = self.total_no_of_candidates_required * self.salary_per_person

	def calculate_benefit_cost_to_company(self):
		total = 0
		if self.other_benefits:
			for benefit in self.other_benefits:
				total += benefit.cost if benefit.cost else 0
		self.benefit_cost_to_company = total

	def calculate_total_cost_to_company(self):
		self.total_cost_to_company = self.total_cost_in_salary + self.benefit_cost_to_company

	def validate_recruiter_assigned(self):
		if not self.recruiter_assigned:
			frappe.throw(_('Recruiter Assigned is a Mandatory Field to Submit.!'))

	def validate_with_erf_request(self):
		erf_request = frappe.get_doc('ERF Request', self.erf_request)
		if erf_request.docstatus != 1:
			frappe.throw(_('ERF Request should be submitted.'))
		if erf_request.status != 'Accepted':
			frappe.throw(_('ERF Request should be Accepted.'))
		if erf_request.department != self.department:
			frappe.throw(_('The Department in ERF Request and ERF Should be the Same.'))
		if erf_request.designation != self.designation:
			frappe.throw(_('The Designation in ERF Request and ERF Should be the Same.'))
		if erf_request.reason_for_request != self.reason_for_request:
			frappe.throw(_('The Reason for Request in ERF Request and ERF Should be the Same.'))
		if erf_request.number_of_candidates_required < self.total_no_of_candidates_required:
			frappe.throw(_('Total Number Candidates Required Should not exceed ERF Request.'))
		erf_exists = frappe.db.exists('ERF', dict(erf_request = self.erf_request,
			docstatus = 1, name = ('!=', self.name)))
		if erf_exists:
			frappe.throw(_("""Submitted ERF <b><a href="#Form/ERF/{0}">{0}</a></b> exists \
			for ERF Request {1}""").format(erf_exists, self.erf_request))

	def set_other_benefits(self):
		if self.is_new() and not self.other_benefits:
			options = ['Company Provided Car', 'Mobile with Line', 'Health Insurance']
			for option in options:
				benefit = self.append('other_benefits')
				benefit.benefit = option

def create_job_opening_from_erf(erf):
	job_opening = frappe.new_doc("Job Opening")
	job_opening.job_title = erf.erf_code+'-'+erf.designation+'-'+erf.department
	job_opening.designation = erf.designation
	job_opening.department = erf.department
	job_opening.one_fm_erf = erf.name
	employee = frappe.db.exists("Employee", {"user_id": erf.owner})
	job_opening.one_fm_hiring_manager = employee if employee else ''
	job_opening.one_fm_no_of_positions_by_erf = erf.total_no_of_candidates_required
	job_opening.one_fm_job_opening_created = today()
	job_opening.one_fm_minimum_experience_required = erf.minimum_experience_required
	job_opening.one_fm_maximum_experience_required = erf.maximum_experience_required
	job_opening.one_fm_minimum_age_required = erf.minimum_age_required
	job_opening.one_fm_maximum_age_required = erf.maximum_age_required
	job_opening.one_fm_performance_profile = erf.performance_profile
	description = set_description_by_performance_profile(job_opening, erf)
	if description:
		job_opening.description = description
	set_erf_skills_in_job_opening(job_opening, erf)
	set_erf_language_in_job_opening(job_opening, erf)
	job_opening.save(ignore_permissions = True)

def set_description_by_performance_profile(job_opening, erf):
	if erf.performance_profile and erf.objectives and erf.key_results:
		template = get_job_openig_description_template()
		return frappe.render_template(
			template, dict(
				objectives=erf.objectives,
				key_results=erf.key_results
			)
		)

def get_job_openig_description_template():
	return """
		{% if objectives %}
		<div>
			<b><u>Objectives:</u></b>
		</div>
		<div style="overflow-x: auto;">
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<td><b>Objective</b></td>
						<td><b>Type</b></td>
						<td><b>Time Frame</b></td>
					</tr>
				</thead>
				<tbody>
					{% for item in objectives %}
						<tr>
							<td>{{ item.objective }}</td>
							<td class='text-right'>
								{{ item.type }}
							</td>
							<td class='text-right'>
								{{ item.time_frame }}
							</td>
						</tr>
					{% endfor %}
				</tbody>
			</table>
		</div>
		{% if key_results %}
		<div>
			<b><u>Key Results:</u></b>
		</div>
		<div>
			<table class="table table-bordered table-hover">
				<tbody>
					<tr>
						<td><b>Key Result</b></td>
						<td><b>Objective</b></td>
						<td><b>Target To Be Achieved by</b></td>
					</tr>
					{% for item in key_results %}
						<tr>
							<td>{{ item.key_result }}</td>
							<td class='text-right'>
								{{ item.objective }}
							</td>
							<td class='text-right'>
								{{ item.target_to_be_achieved_by }}
							</td>
						</tr>
					{% endfor %}
				</tbody>
			</table>
		</div>
		{% endif %}
		{% endif %}
	"""

def set_erf_language_in_job_opening(job_opening, erf):
	if erf.languages:
		for language in erf.languages:
			lang = job_opening.append('one_fm_languages')
			lang.language = language.language
			lang.language_name = language.language_name
			lang.speak = language.speak
			lang.read = language.read
			lang.write = language.write
			lang.expert = language.expert

def set_erf_skills_in_job_opening(job_opening, erf):
	if erf.designation_skill:
		for skill in erf.designation_skill:
			jo_skill = job_opening.append('one_fm_designation_skill')
			jo_skill.skill = skill.skill
			jo_skill.one_fm_proficiency = skill.one_fm_proficiency
