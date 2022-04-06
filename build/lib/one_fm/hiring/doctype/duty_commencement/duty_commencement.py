# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc, make_employee_from_job_offer, update_onboarding_doc_workflow_sate
from frappe.utils import today, getdate, cstr
from frappe import _

class DutyCommencement(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()

		if getdate(self.date_of_joining) < getdate(self.posting_date):
			frappe.msgprint(_("Date of joining is before duty commencement posting date"), alert=True)

		self.set_progress()
		self.update_salary_details_from_job_offer()

	def validate_workflow(self):
		if self.workflow_state == "Applicant Signed and Uploaded" and not self.employee:
			msg = """
				No Employee created for {employee_name}. Please create employee from Onboard Employee
				<a href='{url}'>{onboard_employee}</a>.
			"""
			from frappe.utils.data import get_absolute_url
			frappe.msgprint(_(msg.format(
				employee_name = self.employee_name,
				url = get_absolute_url('Onboard Employee', self.onboard_employee),
				onboard_employee = self.onboard_employee
				)
			))

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
		update_onboarding_doc(self)
		update_onboarding_doc_workflow_sate(self)

	def on_update(self):
		self.set_progress()
		self.validate_submit()
		self.validate_workflow()
		update_onboarding_doc(self)

	def validate_submit(self):
		if self.workflow_state == 'Applicant Signed and Uploaded':
			if not self.attach_duty_commencement:
				frappe.throw(_("Attach Signed Duty Commencement!"))

	def auto_checkin_candidate(self):
		"""This method creates a Shift Assignment and auto checks-in the employee if current time is past shift start time."""
		try:
			# Create shift assignment if doj is today
			if getdate(self.date_of_joining) == getdate():
				if not frappe.db.exists("Shift Assignment", {'employee': self.employee, 'start_date': self.date_of_joining}):
					shift_assignment = frappe.new_doc("Shift Assignment")
					shift_assignment.start_date = self.date_of_joining
					shift_assignment.employee = self.employee
					shift_assignment.post_type = self.post_type
					shift_assignment.shift = self.operations_shift
					shift_assignment.site = self.operations_site
					shift_assignment.project = self.project
					shift_assignment.roster_type = "Basic"
					shift_assignment.save(ignore_permissions=True)
					shift_assignment.submit()
					frappe.msgprint(_("Shift Assignment created for today for this employee."), alert=True, indicator='green')

					# Get current time in hh:mm:ss
					current_time = frappe.utils.now().split(" ")[1].split(".")[0] # yyyy-mm-dd hh:mm:ss:ms => hh:mm:ss
					# Fetch shift start and end time
					shift_start_time = frappe.db.get_value("Operations Shift", {'name': self.operations_shift}, ["start_time"]) # => hh:mm:ss
					if not shift_start_time:
						frappe.throw(_("Could not auto checkin employee. No start time set for duty commencement shift"))

					# Convert "hh:mm:ss" to "hhmmss"
					current_time_str_list = cstr(current_time).split(":")
					shift_start_time_str_list = cstr(shift_start_time).split(":")
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
						checkin.operations_shift = self.operations_shift
						site = frappe.db.get_value("Operations Shift", {'name': self.operations_shift}, ["site"])
						site_location = frappe.db.get_value("Operations Site", {'name': site}, ["site_location"])
						latitude, longitude = frappe.db.get_value("Location", {'name': site_location}, ["latitude", "longitude"])
						checkin.time = frappe.utils.now().split(".")[0]
						checkin.device_id = cstr(latitude) + "," + cstr(longitude)
						checkin.skip_auto_attendance = 0
						checkin.save(ignore_permissions=True)
						frappe.msgprint(_("Auto checked-in employee as his shift has already started on date of joining."), alert=True, indicator='green')
					else:
						frappe.msgprint(_("Please inform employee to check in at shift start time."), alert=True, indicator='orange')

					frappe.db.commit()

				else:
					frappe.msgprint(_("Shift Assignment already created for this employee on Duty Commencement start date."), alert=True, indicator='orange')

			else:
				frappe.msgprint(_("Make sure to roster employee before Duty Commencement start date."), alert=True, indicator='orange')

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
