# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError
from frappe.utils import today, get_url, getdate
from frappe.utils.data import get_url_to_form
from frappe.utils.user import get_user_fullname, get_users_with_role
from frappe import _
from one_fm.one_fm.calendar_event.meetFunc import CalendarEvent
from one_fm.api.notification import create_notification_log
from one_fm.processor import sendemail
from one_fm.utils import validate_mandatory_fields, get_mandatory_fields, create_message_with_details

class ERF(Document):
	def onload(self):
		if self.docstatus == 0 and not self.okr_workshop_with:
			self.okr_workshop_with = frappe.db.get_value('Hiring Settings', None, 'hr_for_a_quick_workshop')
		if self.okr_workshop_with:
			self.set_onload('okr_workshop_with_full_name', get_user_fullname(self.okr_workshop_with))
		self.set_onload('erf_approver', get_erf_approver(self.reason_for_request))

	def validate(self):
		if self.is_new():
			self.status = "Open"
		if not self.erf_requested_by:
			self.erf_requested_by = frappe.session.user
		if not self.erf_requested_by_name and self.erf_requested_by:
			self.erf_requested_by_name = get_user_fullname(self.erf_requested_by)
		self.validate_attendance_by_timesheet()
		self.manage_assigned_recruiter()
		self.validate_date()
		self.validate_languages()
		# self.set_other_benefits()
		self.validate_type_of_license()
		self.set_salary_structure_from_grade()
		self.set_salary_details()
		self.calculate_salary_per_person()
		self.calculate_total_cost_in_salary()
		# self.calculate_benefit_cost_to_company()
		# self.calculate_total_cost_to_company()
		self.validate_type_of_travel()
		self.validate_interview_rounds()

	def validate_interview_rounds(self):
		if self.number_of_interview_rounds and self.number_of_interview_rounds != len(self.interview_rounds):
			frappe.throw(_("Number of rows of the 'Intreview Rounds' must be equal to 'Number of Interview Rounds'!"))

		if self.hiring_method == 'Bulk Recruitment' and self.number_of_interview_rounds < 1:
			frappe.throw(_("Minimum one intreview rounds must be added for bulk recruitment!"))

	def validate_attendance_by_timesheet(self):
		if self.attendance_by_timesheet:
			self.shift_working = False
			self.operations_shift = ''
			self.default_shift = ''

	@frappe.whitelist()
	def draft_erf_to_hrm_for_submit(self):
		self.draft_erf_to_hrm = True
		self.status = 'Draft'
		self.save()
		self.notify_hrm_to_submit()

	def notify_hrm_to_submit(self):
		hrm_to_submit = frappe.db.get_value('Hiring Settings', None, 'hrm_to_fill_hr_and_salary_compensation')
		if hrm_to_submit:
			send_email(self, [hrm_to_submit])
			frappe.msgprint(_('{0}, will be notified via email.').format(frappe.db.get_value('User', hrm_to_submit, 'full_name')))

	def after_insert(self):
		frappe.db.set_value(self.doctype, self.name, 'erf_code', self.name)
		self.reload()

	def validate_type_of_travel(self):
		if self.travel_required and not self.type_of_travel:
			frappe.throw(_('Type of Travel is Mandatory Field.!'))

	def calculate_total_cost_in_salary(self):
		if self.number_of_candidates_required > 0 and self.salary_per_person > 0:
			self.total_cost_in_salary = self.number_of_candidates_required * self.salary_per_person

	def calculate_benefit_cost_to_company(self):
		total = 0
		if self.other_benefits:
			for benefit in self.other_benefits:
				total += benefit.cost if benefit.cost else 0
		self.benefit_cost_to_company = total

	def calculate_total_cost_to_company(self):
		self.total_cost_to_company = self.total_cost_in_salary + self.benefit_cost_to_company

	def calculate_salary_per_person(self):
		total = 0
		if self.salary_details:
			for salary_detail in self.salary_details:
				total += salary_detail.amount if salary_detail.amount else 0
		self.salary_per_person = total

	def validate_total_required_candidates(self):
		total = 0
		if self.gender_height_requirement:
			for required_candidate in self.gender_height_requirement:
				total += required_candidate.number
		if self.number_of_candidates_required != total:
			frappe.throw(_('Total Number Candidates Required Should be {0}.').format(self.number_of_candidates_required))

	def set_salary_details(self):
		if self.salary_structure and not self.salary_details:
			salary_structure = frappe.get_doc('Salary Structure', self.salary_structure)
			if salary_structure.earnings:
				for earning in salary_structure.earnings:
					salary_detail = self.append('salary_details')
					salary_detail.salary_component = earning.salary_component
					salary_detail.amount = earning.amount

	def set_salary_structure_from_grade(self):
		if self.grade and not self.salary_structure and not self.salary_details:
			self.salary_structure = frappe.db.get_value('Employee Grade', self.grade, 'default_salary_structure')

	def validate_type_of_license(self):
		if self.driving_license_required and not self.type_of_license:
			frappe.throw(_('Type of License is Mandatory Field.!'))

	def set_other_benefits(self):
		if self.is_new() and not self.other_benefits:
			options = ['Company Provided Car', 'Mobile with Line', 'Health Insurance']
			for option in options:
				benefit = self.append('other_benefits')
				benefit.benefit = option

	def validate_languages(self):
		if self.languages:
			for language in self.languages:
				if not language.read and not language.write and not language.speak:
					frappe.throw(_("Select Language for Speak, Read or Write.!"))

	def validate_date(self):
		if getdate(self.erf_initiation) > getdate(self.expected_date_of_deployment):
			frappe.throw(_("Expected Date of Deployment of an ERF cannot be before ERF Initiation Date"))
		if getdate(self.expected_date_of_deployment) < getdate(today()):
			frappe.throw(_("Expected Date of Deployment of an ERF cannot be before Today"))

	def manage_assigned_recruiter(self):
		if not self.need_to_assign_more_recruiter:
			self.secondary_recruiter_assigned = ''
		if not self.is_new():
			remove_recruiter_assignment_from_task(self)

	def on_update(self):
		assign_recruiter_to_project_task(self)
		if self.status in ['Closed',]:
			self.close_job_opening()

	def before_cancel(self):
		self.status = 'Cancelled'
		self.close_job_opening()

	def on_submit(self):
		self.validate_total_required_candidates()
		self.erf_finalized = today()
		self.notify_recruitment_manager()
		# self.notify_approver()
		self.reload()

	def notify_recruitment_manager(self):
		try:
			role_profile = frappe.db.get_list("Role Profile", {"role_profile": ["IN", ["Recruitment Manager", "Director"]]}, pluck="name")
			if role_profile:
				manager_emails = frappe.db.get_list("User", {"role_profile_name": ["IN", role_profile]}, pluck="name")
				if manager_emails:
					title = f"Urgent Notification: {self.name} Requires Your Immediate Review"
					context = {
						"erf_name" : self.name,
						"designation": self.designation,
						"requester": self.erf_requested_by_name,
						"reason_for_request": self.reason_for_request,
						"doc_link": get_url_to_form(self.doctype, self.name),
						"project": self.project,
						"department": self.department,
						"date_of_deployment": self.expected_date_of_deployment
					}
					msg = frappe.render_template('one_fm/templates/emails/notify_recruitment_manager.html', context=context)
					frappe.enqueue(sendemail, recipients=manager_emails, subject=title, content=msg, at_front=True, is_async=True)
					frappe.msgprint(_('Recruitment manager will be notified by email.'))
		except:
			frappe.log_error(frappe.get_traceback(), "Error while sending mail to recruitment manager(ERF) ")





	@frappe.whitelist()
	def job_opening_status(self):
		data = len(frappe.db.get_list('Job Opening', filters={
			'one_fm_erf':self.name, 'status':'Open', 'publish':1
		}))
		return {'opening': data}

	@frappe.whitelist()
	def close_job_opening(self):
		job_openings = frappe.db.get_list("Job Opening", filters={'one_fm_erf':self.name})
		for row in job_openings:
			job_opening = frappe.get_doc("Job Opening", row.name)
			job_opening.db_set('publish', 0)
			job_opening.db_set('status', 'Closed')

		frappe.msgprint('Job Opening Closed')

	def validate_submit_to_hr(self):
		if not self.draft_erf_to_hrm and self.docstatus == 1:
			frappe.throw(_('Submit to HR Manager to fill Salary Compensation Budget and HR Details!'))

	def notify_approver(self):
		erf_approver = get_erf_approver(self.reason_for_request)
		if erf_approver and len(erf_approver) > 0:
			send_email(self, erf_approver)
			frappe.msgprint(_('Recruitment Manager Will Notified By Email.'))

	def on_update_after_submit(self):
		self.validate_total_required_candidates()
		if self.workflow_state == "Accepted":
			# self.validate_submit_to_hr()
			# if not self.hiring_method:
			# 	frappe.throw(_("Please set Hiring Method in HR section"))
			# self.validate_recruiter_assigned()
			self.accept_or_decline(status=self.workflow_state)
		if frappe.db.get_value('Hiring Settings', None, 'close_erf_automatically'):
			if self.erf_employee and len(self.erf_employee) == self.number_of_candidates_required:
				self.db_set('status', 'Closed')

	def notify_finance_department(self):
		fin_department = frappe.db.get_value('Hiring Settings', None, 'notify_finance_department_for_job_offer_salary_advance')
		if fin_department:
			message = """
				<p>
					A new ERF for the {0} position has been raised, employees selected will be receiving salary advance.
					Subsequently during the hiring process you will be notified the amount for each employee when the
					applicant is selected and offered.
				</p>
			""".format(self.designation)
			sendemail(
				recipients= [fin_department],
				subject='ERF {0} for {1}'.format(self.status, self.designation),
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name
			)
			frappe.msgprint(_('Finance Department Will be Notified By Email.'))

	def notify_recruiter_and_requester(self):
		if self.status in ['Accepted', 'Rejected']:
			recipients = [self.erf_requested_by, self.recruiter_assigned]
			do_not_notify_requester = frappe.db.get_value('Hiring Settings', None, 'do_not_notify_requester')
			if do_not_notify_requester == '1':
				recipients = [self.recruiter_assigned]
			if self.erf_requested_by == self.recruiter_assigned:
				recipients = [self.erf_requested_by]
			if self.need_to_assign_more_recruiter and self.secondary_recruiter_assigned:
				recipients.append(self.secondary_recruiter_assigned)
			send_email(self, recipients)
			msg = _('{0} and {1} Will be Notified By Email.').format(self.erf_requested_by, self.recruiter_assigned)
			if self.erf_requested_by == self.recruiter_assigned:
				msg = _('{0} Will be Notified By Email.').format(self.erf_requested_by)
			elif do_not_notify_requester == '1':
				msg = _('{0} Will be Notified By Email.').format(self.recruiter_assigned)
			frappe.msgprint(msg)

	def notify_grd_supervisor(self):
		grd_supervisor = frappe.db.get_value('GRD Settings', None, 'default_grd_supervisor')
		page_link = get_url(self.get_url())
		subject = _("Attention: You Are Requested to Fill GRD Section in ERF")
		message = "<p>Kindly, you are requested to fill the PAM File Number and PAM Designation for ERF: {0}  <a href='{1}'></a></p>".format(self.name,page_link)
		create_notification_log(subject, message, [grd_supervisor], self)

	def notify_gsd_department(self):
		gsd_department = frappe.db.get_value('Hiring Settings', None, 'notify_gsd_on_erf_approval')
		if gsd_department:
			message = """
				<p>ERF is Approved for the Position {0}</p>
				<p>Details:
					<ol>
						<li>Project: {1}</li>
						<li>Grade: {2}</li>
						<li>Number of Employees: {3}</li>
						<li>Position: {0}</li>
			""".format(self.designation, self.project, self.grade, self.number_of_candidates_required)
			if self.is_uniform_needed_for_this_job:
				message += """<li>Uniform required for the employees</li>"""
			message += """</ol></p>
			<p>
				<table class="table table-bordered table-hover">
					<thead>
						<tr>
							<td><b>Gender</b></td>
							<td><b>Nationality</b></td>
							<td><b>Quantity</b></td>
						</tr>
					</thead>
					<tbody>
			"""
			for item in self.gender_height_requirement:
				message += "<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>".format(item.gender, item.nationality,
					item.number)
			message += "</tbody></table></p>"
			sendemail(
				recipients= [gsd_department],
				subject='ERF - {0} - {1}'.format(self.status, self.designation),
				message=message,
				reference_doctype=self.doctype,
				reference_name=self.name
			)
			frappe.msgprint(_('GSD Department Will be Notified By Email.'))

	def validate_recruiter_assigned(self):
		if not self.recruiter_assigned:
			frappe.throw(_('Recruiter Assigned is a Mandatory Field to Submit.!'))
		if self.need_to_assign_more_recruiter and not self.secondary_recruiter_assigned:
			frappe.throw(_('If You Need Assign One More Recruiter, Please fill the Secondary Recruiter Assigned.!'))

	@frappe.whitelist()
	def create_event_for_okr_workshop(self):
		user= 'Onefm'
		start_time= "{0}".format(self.schedule_for_okr_workshop_with_recruiter)
		summary= 'ERF meeting'
		location= 'Hawally'
		description= 'Employee Requisition meeting'
		erf_requester_email='{}'.format(self.erf_requested_by)
		secondary_hr_manager_email = 'y.alluqman@one-fm.com'
		hr_manager_email= '{}'.format(self.okr_workshop_with)

		CalendarEvent(user).create_event(start_time, summary, location, description, erf_requester_email, hr_manager_email, secondary_hr_manager_email)
		self.draft_erf_to_hrm_for_submit()
		if self.schedule_for_okr_workshop_with_recruiter and self.okr_workshop_with:
			return set_event_for_okr_workshop(self)

	@frappe.whitelist() #adding permission while Accepting
	def accept_or_decline(self, status, reason_for_decline=None):
		# self.status = status
		# self.reason_for_decline = reason_for_decline
		# self.save()
		self.notify_recruiter_and_requester()
		if status == "Closed":
			self.workflow_state = "Closed"
			self.status = "Closed"
			self.save()
		elif self.status == 'Accepted':
			assign_recruiter_to_project_task(self)
			self.notify_grd_supervisor()
			self.notify_gsd_department()
			if self.provide_salary_advance:
				self.notify_finance_department()
			if not frappe.db.exists("Job Opening", {'one_fm_erf':self.name}):
				create_job_opening_from_erf(self)
		self.reload()



def get_erf_approver(reason_for_request):
	erf_approver_role = 'Unplanned ERF Approver' if reason_for_request == 'UnPlanned' else 'ERF Approver'
	return get_users_with_role(erf_approver_role)

def create_job_opening_from_erf(erf):
	job_opening = frappe.new_doc("Job Opening")
	# Set unique job_title
	# since job_title will be set a route in Job Opening and the route is set as name in Job Opening
	job_opening.job_title = erf.job_title+'('+erf.name+')'
	job_opening.job_title_in_arabic = job_opening.job_title
	job_opening.designation = erf.designation
	job_opening.employment_type = erf.employment_type
	job_opening.department = erf.department
	job_opening.one_fm_erf = erf.name
	employee = frappe.db.exists("Employee", {"user_id": erf.owner})
	job_opening.one_fm_hiring_manager = employee if employee else ''
	job_opening.one_fm_no_of_positions_by_erf = erf.number_of_candidates_required
	job_opening.one_fm_job_opening_created = today()
	job_opening.one_fm_minimum_experience_required = erf.minimum_experience_required
	job_opening.one_fm_performance_profile = erf.performance_profile
	description = get_description_by_performance_profile(job_opening, erf)
	if description:
		job_opening.description = description
	set_erf_skills_in_job_opening(job_opening, erf)
	set_erf_language_in_job_opening(job_opening, erf)
	job_opening.save(ignore_permissions = True)

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

def get_description_by_performance_profile(job_opening, erf):
	if erf.performance_profile:
		template = get_job_openig_description_template()
		okr = frappe.get_doc('OKR Performance Profile', erf.performance_profile)
		return frappe.render_template(
			template, dict(
				objective_description=okr.description,
				objectives=okr.objectives
			)
		)

def get_job_openig_description_template():
	return """
		{% if objectives %}
		<div>
			<p>{{ objective_description }}</p>
			<br/>
			<b><u>Objectives:</u></b><br/>
			{% for item in objectives %}
				{{ item.objective }}<br/>
			{% endfor %}
		</div>
		{% endif %}
	"""

def send_email(doc, recipients):
	page_link = get_url(doc.get_url())
	message = "<p>Here is the ERF <a href='{0}'>{1}</a> requested by {2}. Please Review it and take action.</p>".format(page_link, doc.name,doc.erf_requested_by_name)
	mandatory_field, labels = get_mandatory_fields(doc.doctype, doc.name)

	if mandatory_field and labels:
		message = create_message_with_details(message, mandatory_field, labels)

	if doc.status == 'Declined' and doc.reason_for_decline:
		message = "<p>ERF <a href='{0}'>{1}</a> is Declined due to {2}</p>".format(page_link, doc.name, doc.reason_for_decline)
	sendemail(
		recipients= recipients,
		subject='ERF - {0} - {1}'.format(doc.status, doc.designation),
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def remove_recruiter_assignment_from_task(doc):
	recruiter_list = []
	old_recruiter_assigned = frappe.db.get_values('ERF', filters={'name': doc.name}, fieldname=["recruiter_assigned", "secondary_recruiter_assigned"], as_dict=True)
	for d in old_recruiter_assigned:
		if d:
			if d.recruiter_assigned and d.recruiter_assigned != doc.recruiter_assigned:
				recruiter_list.append(d.recruiter_assigned)
			if d.secondary_recruiter_assigned and d.secondary_recruiter_assigned != doc.secondary_recruiter_assigned:
				recruiter_list.append(d.secondary_recruiter_assigned)

	if recruiter_list:
		from frappe.desk.form.assign_to import remove as remove_assignment
		task_list = frappe.get_list('Task', filters={'project': doc.project_for_recruiter, 'status': 'Open'}, fields=["name"])
		for recruiter in recruiter_list:
			for task in task_list:
				remove_assignment('Task', task.name, recruiter)

def assign_recruiter_to_project_task(doc):
	if doc.recruiter_assigned and doc.project_for_recruiter:
		task_list = frappe.get_list('Task', filters={'project': doc.project_for_recruiter, 'status': 'Open'}, fields=["name"])
		recruiter_list = [doc.recruiter_assigned]
		if doc.need_to_assign_more_recruiter and doc.secondary_recruiter_assigned:
			recruiter_list.append(doc.secondary_recruiter_assigned)
		task_assign_to_recruiter(doc, recruiter_list, task_list)

def task_assign_to_recruiter(doc, recruiter_list, task_list):
	for recruiter in recruiter_list:
		for task in task_list:
			try:
				add_assignment({
					'doctype': 'Task',
					'name': task.name,
					'assign_to': [recruiter],
					'description': _('Please review the ERF')
				})
			except DuplicateToDoError:
				frappe.message_log.pop()
				pass


@frappe.whitelist()
def get_project_details(project):
	operation_site_list = frappe.get_list('Operations Site', filters={'project': project}, fields=['site_location'])
	location_list = []
	for operation_site in operation_site_list:
		if operation_site.site_location not in location_list:
			location_list.append(operation_site.site_location)
	return {'location_list': location_list}

def set_event_for_okr_workshop(doc):
	message = "Dear {0},<br/>".format(get_user_fullname(doc.okr_workshop_with))
	if doc.help_hr_to_create_okr:
		message += """{0} has suggested the following for the performance profile of {1} Position.
		<br/>{2}<br/>Also,<br/>""".format(doc.erf_requested_by_name, doc.designation, doc.help_hr_to_create_okr)
	message += """
		{0}, would want conduct a Performance Profile workshop on {1},
		you may please contact {0} to confirm the schedule.
		<br/>
		Email: {2}
	""".format(doc.erf_requested_by_name, doc.schedule_for_okr_workshop_with_recruiter, doc.erf_requested_by)

	sendemail(
		recipients = doc.okr_workshop_with,
		sender = frappe.db.get_value('User', frappe.session.user, 'email'),
		subject = _("For a Quick Workshop to Create Performance Profile"),
		message = _(message)
	)
	frappe.msgprint(_("Email sent to {0}").format(doc.okr_workshop_with))
	event = frappe.new_doc('Event')
	event.subject = 'Test Subject'
	event.event_category = 'Meeting'
	event.event_type = 'Private'
	event.starts_on = doc.schedule_for_okr_workshop_with_recruiter
	event.save(ignore_permissions=True)
	# Share the event to get notified by email.
	frappe.share.add('Event', event.name, doc.okr_workshop_with, write=1, share=1,
		flags={"ignore_share_permission": True})
	return event

@frappe.whitelist()
def set_user_fullname(user):
	return get_user_fullname(user)

@frappe.whitelist()
def recruitment_manager_check(user: str):
	role_profile = frappe.db.get_value('Role Profile', {"role_profile":["in",['Recruitment Team Leader',"Recruitment Manager"]]}, "name")
	if role_profile:
		return frappe.db.exists('User', {"role_profile_name": role_profile, "name": user})
	return False
