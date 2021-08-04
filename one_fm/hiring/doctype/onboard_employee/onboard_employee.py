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
from frappe.utils import now

class OnboardEmployee(Document):
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
			wc.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_duty_commencement(self):
		if self.work_contract_status == "Applicant Signed":
			duty_commencement = frappe.new_doc('Duty Commencement')
			duty_commencement.onboard_employee = self.name
			duty_commencement.save(ignore_permissions=True)

	@frappe.whitelist()
	def create_employee(self):
		if self.duty_commencement_status == 'Applicant Signed and Uploaded':
			if not self.reports_to:
				frappe.throw(_("Select reports to user!"))
			elif self.job_offer:
				employee = make_employee_from_job_offer(self.job_offer)
				employee.reports_to = self.reports_to
				if not employee.one_fm_civil_id:
					employee.one_fm_civil_id = 'dsdsf' #self.civil_id
				if not employee.one_fm_nationality:
					employee.one_fm_nationality = self.nationality
				employee.one_fm_first_name_in_arabic = employee.employee_name
				employee.permanent_address = "Test"
				employee.reports_to = self.reports_to
				employee.save(ignore_permissions=True)
				self.employee = employee.name
				self.save(ignore_permissions=True)

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
	def create_bank_account(self):
		if self.employee and not self.bank_account:
			create_account = True
			if self.new_bank_account_needed and not self.attach_bank_form:
				create_account = False
				frappe.msgprint(_("Please attach Bank Form to create New Bank Account."))
			if create_account:
				if self.account_name and self.bank:
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
					frappe.msgprint(_('To Create Bank Account, Set Account Name and Bank !'))

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
