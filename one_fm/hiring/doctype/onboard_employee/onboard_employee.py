# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from one_fm.hiring.doctype.candidate_orientation.candidate_orientation import create_candidate_orientation
from one_fm.hiring.doctype.work_contract.work_contract import employee_details_for_wc
from one_fm.hiring.utils import make_employee_from_job_offer
from frappe.utils import now, today, getdate
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request

class OnboardEmployee(Document):

	def validate(self):
		if not self.number_of_days_off:
			frappe.throw(_("Please set the number of days off."))
		if self.day_off_category == "Weekly":
			if frappe.utils.cint(self.number_of_days_off) > 7:
				frappe.throw(_("Number of days off cannot be more than a week."))
		elif self.day_off_category == "Monthly":
			if frappe.utils.cint(self.number_of_days_off) > 30:
				frappe.throw(_("Number of days off cannot be more than a month."))


	def on_update(self):
		if self.workflow_state == 'Inform Applicant':
			self.inform_applicant()

	def on_update_after_submit(self):
		self.validate_transition()
		self.validate_on_complete()

	def validate_transition(self):
		if self.workflow_state == 'Applicant Attended' and not self.applicant_attended:
			self.mark_applicant_attended()
			self.reload()

		if self.workflow_state == 'Work Contract' and not self.work_contract:
			if self.electronic_signature_status == 1:
				self.create_work_contract()
				self.reload()
			else:
				frappe.throw(_("Please Update Electronic Signature Declaration with Applicant Signature to Proceed"))

		if self.workflow_state == 'Declaration of Electronic Signature':
			self.create_declaration_of_electronic_signature()
			self.reload()

		if self.workflow_state == 'Duty Commencement' and not self.duty_commencement:
			self.create_duty_commencement()
			self.reload()

		if self.workflow_state == 'Bank Account':
			if not self.duty_commencement:
				frappe.throw(_("Duty Commencement is not created for the Applicant"))
			if not self.employee:
				frappe.throw(_("Employee is not created for the Applicant"))
			elif not self.bank_account:
				self.create_bank_account()

	def validate_on_complete(self):
		if self.workflow_state == 'Completed' and not frappe.db.get_value('Employee', self.employee, 'enrolled'):
			frappe.throw(_("Employee has not yet registered/enrolled in the mobile app"))

	def validate_employee_creation(self):
		if self.docstatus != 1:
			frappe.throw(_("Submit this to create the Employee record"))
		else:
			for activity in self.activities:
				if not activity.required_for_employee_creation:
					continue
				else:
					task_status = frappe.db.get_value("Task", activity.task, "status")
					if task_status not in ["Completed", "Cancelled"]:
						frappe.throw(_("All the mandatory Task for employee creation hasn't been done yet."), IncompleteTaskError)

	@frappe.whitelist()
	def inform_applicant(self):
		if not self.orientation_location and not self.orientation_on:
			frappe.throw(_('To inform applicant, You need to set Location and Orientation On!'))
		else:
			subject = "<p>Dear {0} You Orientation Program is scheduled at {1} on {2}</p>".format(self.employee_name, self.orientation_on, self.orientation_location)
			message = subject + "<p>Please be there in time and documents requested</p>"
			if self.email_id:
				frappe.sendmail(recipients= [self.email_id], subject=subject, message=message,
					reference_doctype=self.doctype, reference_name=self.name)
			self.informed_applicant = True
			self.save(ignore_permissions=True)

	@frappe.whitelist()
	def mark_applicant_attended(self):
		self.applicant_attended_orientation = now()
		self.applicant_attended = True
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_work_contract(self):
		self.validate_orientation()
		if not frappe.db.exists('Work Contract', {'onboard_employee': self.name}):
			filters = employee_details_for_wc(self)
			filters['doctype'] = 'Work Contract'
			filters['onboard_employee'] = self.name
			wc = frappe.new_doc('Work Contract')
			for filter in filters:
				wc.set(filter, filters[filter])

			for applicant_docs in self.applicant_documents:
				doc_required = wc.append('documents')
				fields = ['document_required', 'attach', 'type_of_copy']
				for field in fields:
					doc_required.set(field, applicant_docs.get(field))

			wc.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_declaration_of_electronic_signature(self):
		"""
		Create declaration_of_electronic_signature from onboard employee doc.
		"""
		if not frappe.db.exists('Electronic Signature Declaration', {'onboard_employee': self.name}):
			doc = frappe.new_doc('Electronic Signature Declaration')
			doc.onboard_employee = self.name
			doc.employee_name = self.employee_name
			doc.employee_name_in_arabic = self.employee_name_in_arabic
			doc.nationality = self.nationality
			doc.civil_id = self.civil_id
			doc.company = self.company
			doc.declarationen = "<h4>I,  {0}, nationality  {1}, holding civil ID no. {2} the undersigned, acknowledge that the signature written at the bottom of this acknowledgment is my own, certified, and valid signature, and that I acknowledge the acceptance and enforcement of this signature against me and against others, and I authorize {3} company / to adopt this signature as a legally valid electronic signature.</h4>".format(self.employee_name,self.nationality,self.civil_id,self.company)
			doc.declarationar = "<h4>{0} قر أنا الموقع أدناه  / ، واحمل بطاقة مدنية ر {1} الجنسية({2}) بأن التوقيع المدون أسفل هذا اإلقرار و التوقيع الخاص بي معتمد وساري ،وأنني اقر بقبول ونفاذ هذا التوقيع في مواجهتي مواجهة الغير ، باعتماد {3}وأنني افوض شركة / .هذا التوقيع كتوقيع إلكتروني ساري المفعول قانوناً</h4>".format(self.employee_name_in_arabic,frappe.db.get_value("Nationality", self.nationality, 'nationality_arabic'),self.civil_id,self.company)
			doc.save(ignore_permissions=True)
			doc.submit()

	@frappe.whitelist()
	def create_duty_commencement(self):
		if self.work_contract_status == "Applicant Signed":
			duty_commencement = frappe.new_doc('Duty Commencement')
			duty_commencement.onboard_employee = self.name
			duty_commencement.workflow_state = 'Open'
			duty_commencement.flags.ignore_mandatory = True
			duty_commencement.save(ignore_permissions=True)
		else:
			frappe.throw(_("Work Contract needs to be Signed by Applicant to Create Duty Commencement"))

	@frappe.whitelist()
	def create_employee(self):
		if self.duty_commencement_status == 'Applicant Signed and Uploaded' and not self.employee:
			if not self.leave_policy:
				frappe.throw(_("Select Leave Policy before Creating Employee!"))
			if not self.reports_to:
				frappe.throw(_("Select reports to user!"))
			if self.job_offer:
				employee = make_employee_from_job_offer(self.job_offer)
				employee.reports_to = self.reports_to
				if not employee.one_fm_civil_id:
					employee.one_fm_civil_id = self.civil_id
				if not employee.one_fm_nationality:
					employee.one_fm_nationality = self.nationality
				employee.leave_policy = self.leave_policy
				employee.salary_mode = self.salary_mode
				employee.one_fm_first_name_in_arabic = employee.employee_name
				if self.declaration_of_electronic_signature:
					employee.employee_signature = frappe.get_value("Electronic Signature Declaration",self.declaration_of_electronic_signature,['applicant_signature'])

				employee.permanent_address = "Test"
				employee.one_fm_basic_salary = frappe.db.get_value('Job Offer', self.job_offer, 'base')
				employee.one_fm_pam_designation = frappe.db.get_value('Job Applicant', self.job_applicant, 'one_fm_pam_designation')
				employee.reports_to = self.reports_to
				date_of_joining = frappe.db.get_value('Duty Commencement', self.duty_commencement, 'date_of_joining')
				if date_of_joining:
					employee.date_of_joining = getdate(date_of_joining)
					self.date_of_joining = getdate(date_of_joining)
				employee.save(ignore_permissions=True)
				self.employee = employee.name
				self.save(ignore_permissions=True)
				self.update_duty_commencement()

	def update_duty_commencement(self):
		duty_commencement = frappe.get_doc("Duty Commencement", self.duty_commencement)
		duty_commencement.employee = self.employee
		duty_commencement.save(ignore_permissions=True)
		duty_commencement.auto_checkin_candidate()

	def validate_orientation(self):
		if not self.informed_applicant:
			frappe.throw(_('Applicant not Informed !'))
		if not self.applicant_attended:
			frappe.throw(_('Applicant is not Attended !'))

	@frappe.whitelist()
	def create_rfm_from_eo(self):
		if self.erf:
			erf = frappe.get_doc('ERF', self.erf)
			# erf = frappe.get_doc('ERF', 'ERF-2020-00023')
			if erf.tool_request_item:
				rfm = frappe.new_doc('Request for Material')
				rfm.requested_by = frappe.session.user
				rfm.type = 'Onboarding'
				rfm.erf = erf.name
				rfm.t_warehouse = frappe.db.get_value('Stock Settings', None, 'default_warehouse')
				rfm.schedule_date = self.date_of_joining
				rfm_item = rfm.append('items')
				for item in erf.tool_request_item:
					rfm_item.requested_item_name = item.item
					rfm_item.requested_description = item.item
					rfm_item.qty = item.quantity
					rfm_item.uom = 'Nos'
					rfm_item.schedule_date = self.date_of_joining
				rfm.save(ignore_permissions=True)
				self.request_for_material = rfm.name
				self.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_loan(self):
		if not self.loan_type:
			frappe.throw(_('Please select Loan Type !'))
		else:
			loan = frappe.new_doc("Loan")
			loan.applicant_type = 'Employee'
			loan.applicant = self.employee
			loan.loan_type = self.loan_type
			is_term_loan = frappe.db.get_value('Loan Type', self.loan_type, 'is_term_loan')
			loan.repay_from_salary = is_term_loan
			loan.is_term_loan = is_term_loan
			loan.loan_amount = self.net_loan_amount
			loan.repayment_method = self.repayment_method
			loan.repayment_periods = self.repayment_periods
			loan.monthly_repayment_amount = self.monthly_repayment_amount
			loan.repayment_start_date = self.repayment_start_date
			loan.save(ignore_permissions=True)
			loan.submit()
			self.loan = loan.name
			self.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_employee_id(self):
		if self.employee and not self.employee_id:
			employee_id = frappe.new_doc('Employee ID')
			employee_id.employee = self.employee
			employee_id.reason_for_request = 'New ID'
			employee_id.onboard_employee = self.name
			employee_id.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_user_and_permissions(self):
		if self.company_email:
			# if not frappe.db.exists('User', self.company_email):
			user = frappe.new_doc('User')
			user.first_name = self.employee_name
			user.email = self.company_email
			user.role_profile_name = self.role_profile
			user.save(ignore_permissions = True)
			employee = frappe.get_doc('Employee', self.employee)
			employee.user_id = user.name
			employee.create_user_permission = self.create_user_permission
			employee.save(ignore_permissions=True)
			self.user_created = True
			self.save(ignore_permissions=True)
		else:
			frappe.throw(_('Enter company email to create ERPNext User.!'))

	@frappe.whitelist()
	def create_103_form(self):
		from one_fm.grd.doctype.pifss_form_103.pifss_form_103 import create_103_form_for_onboarding
		create_103_form_for_onboarding(self.employee, self.name)

	@frappe.whitelist()
	def create_mgrp(self):
		from one_fm.grd.doctype.mgrp.mgrp import create_mgrp_form_for_onboarding
		create_mgrp_form_for_onboarding(self.employee, self.name)

	@frappe.whitelist()
	def create_bank_account(self):
		if self.employee and not self.bank_account:
			create_account = True
			# if self.new_bank_account_needed and not self.attach_bank_form:
			# 	create_account = False
			# 	frappe.msgprint(_("Please attach Bank Form to create New Bank Account."))
			if create_account:
				if self.account_name and self.bank and self.iban:
					bank_account = frappe.new_doc('Bank Account')
					bank_account.account_name = self.account_name
					bank_account.bank = self.bank
					bank_account.new_account = self.new_bank_account_needed
					bank_account.party_type = 'Employee'
					bank_account.party = self.employee
					bank_account.attach_bank_form = self.attach_bank_form
					bank_account.onboard_employee = self.name
					bank_account.save(ignore_permissions=True)
				else:
					frappe.throw(_('To Create Bank Account, Set Account Name, Bank and IBAN !'))

	@frappe.whitelist()
	def create_g2g_residency_payment_request(self):
		if self.down_payment_amount and self.down_payment_amount > 0:
			pr = frappe.new_doc("Payment Request")
			pr.update({
				"grand_total": self.down_payment_amount,
				"payment_request_type": "Inward",
				"mode_of_payment": self.g2g_residency_mop,
				"subject": _("Payment Request for {0}").format(self.name),
				"message": _("Payment Request for {0}").format(self.name),
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"party_type": "Job Applicant",
				"party": self.job_applicant,
				"transaction_date": today()
			})

			pr.flags.mute_email = True

			pr.insert(ignore_permissions=True)
			pr.submit()
			frappe.db.commit()
			self.payment_request = pr.name
			self.save(ignore_permissions=True)

	def assign_task_to_users(self, task, users):
		for user in users:
			args = {
				'assign_to' 	:	user,
				'doctype'		:	task.doctype,
				'name'			:	task.name,
				'description'	:	task.description or task.subject,
				'notify':	self.notify_users_by_email
			}
			assign_to.add(args)

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	doc = frappe.get_doc("Employee Onboarding", source_name)
	doc.validate_employee_creation()
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
		target.status = "Active"
	doc = get_mapped_doc("Employee Onboarding", source_name, {
			"Employee Onboarding": {
				"doctype": "Employee",
				"field_map": {
					"first_name": "employee_name",
					"employee_grade": "grade",
				}}
		}, target_doc, set_missing_values)
	return doc
