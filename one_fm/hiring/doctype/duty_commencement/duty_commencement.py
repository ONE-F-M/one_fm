# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc, make_employee_from_job_offer
from frappe.utils import today, getdate, cstr
from frappe import _

class DutyCommencement(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()

		if getdate(self.date_of_joining) < getdate():
			frappe.throw(_("Date of joining cannot be before today"))

		if not self.employee:
			frappe.throw(_("No Employee created for {employee_name}. Please create employee from Onboard Employee.".format(employee_name=self.employee_name)))
		self.set_progress()
		self.update_salary_details_from_job_offer()

	def update_salary_details_from_job_offer(self):
		if not self.salary_details and self.job_offer:
			job_offer = frappe.get_doc('Job Offer', self.job_offer)
			if job_offer.one_fm_salary_details:
				total_salary = 0
				for salary in job_offer.one_fm_salary_details:
					sd = self.append('salary_details')
					sd.salary_component = salary.salary_component
					sd.amount = salary.amount
					if "Basic" in salary.salary_component:
						self.basic_salary = salary.amount
					elif "Transportation" in salary.salary_component:
						self.transportation_salary = salary.amount
					elif "Accommodation" in salary.salary_component:
						self.accommodation_salary = salary.amount
					else:
						self.other_allowances_salary = salary.amount
					total_salary += salary.amount
				self.total_salary = total_salary

	def set_progress(self):
		progress_wf_list = {'Open': 0, 'Submitted for Applicant Review': 20, 'Applicant Signed and Uploaded': 100,
			'Applicant Not Signed': 40, 'Cancelled': 0}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def after_insert(self):
		employee_doc = frappe.get_doc("Employee", self.employee)
		employee_doc.project = self.project
		employee_doc.site = self.operations_site
		employee_doc.shift = self.operations_shift
		employee_doc.date_of_joining = self.date_of_joining
		employee_doc.save(ignore_permissions=True)
		update_onboarding_doc(self)

	def on_update(self):
		self.set_progress()
		self.validate_attachments()
		update_onboarding_doc(self)
		if self.employee:
			self.auto_checkin_candidate()

	def validate_attachments(self):
		if self.workflow_state == 'Applicant Signed and Uploaded':
			if not self.attach_duty_commencement:
				frappe.throw(_("Attach Signed Duty Commencement!"))

	def auto_checkin_candidate(self):
		"""This method creates a Shift Assignment and auto checks-in the employee if current time is past shift start time."""
		try:
			# Create shift assignment if doj is today
			if getdate(self.date_of_joining) == getdate():
				shift_assignment = frappe.new_doc("Shift Assignment")
				shift_assignment.start_date = self.date_of_joining
				shift_assignment.employee = self.employee
				shift_assignment.post_type = self.post_type
				shift_assignment.shift = self.operations_shift
				shift_assignment.site = self.operations_site
				shift_assignment.project = self.project
				shift_assignment.roster_type = "Basic"
				shift_assignment.submit(ignore_permissions=True)

				# Get current time in hh:mm:ss
				current_time = frappe.utils.now().split(" ")[1].split(".")[0] # yyyy-mm-dd hh:mm:ss:ms => hh:mm:ss
	
				# Fetch shift start and end time
				shift_start_time = frappe.db.get_value("Operations Shift", {'name': self.operations_shift}, ["start_time"]) # => hh:mm:ss

				if not shift_start_time:
					frappe.throw(_("Could not auto checkin employee. No start time set for duty commencement shift"))
				
				# Convert "hh:mm:ss" to "hhmmss"
				current_time_str_list = current_time.split(":")
				shift_start_time_str_list = shift_start_time.split(":")
				
				current_time_str = ""
				shift_start_time_str = ""
				for i in current_time_str_list:
					current_time_str += i
				for i in shift_start_time_str_list:
					shift_start_time_str += i

				# If current time is past the shift time, auto check-in employee
				if int(current_time_str) >= int(shift_start_time_str):
					checkin = frappe.new_doc("Employee Checkin")
					checkin.employee = self.employee
					checkin.log_type = "IN"
					checkin.skip_auto_attendance = 0
					checkin.save(ignore_permissions=True)
				else:
					frappe.show_alert("Please inform employee to Checkin at shift start time.", 5)

				frappe.db.commit()
			
			else:
				frappe.show_alert("Make sure to roster this employee before Duty Commencement start date.", 5);
		
		except Exception as e:
			frappe.log_error(e)			

	def on_cancel(self):
		if self.workflow_state == 'Cancelled':
			update_onboarding_doc(self, cancel_oe = True)
		else:
			update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)
