# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MedicalInsurance(Document):
	def validate(self):
		self.valid_work_permit_exists()
		self.update_end_date()

	def update_end_date(self):
		if self.no_of_years and self.no_of_years > 0 and self.start_date:
			self.end_date = frappe.utils.add_years(self.start_date, self.no_of_years)

	def valid_work_permit_exists(self):
		# TODO: Check valid work permit exists for the employee
		pass

	def get_employee_data_from_civil_id(self):
		if self.civil_id:
			employee_id = frappe.db.exists('Employee', {'one_fm_civil_id': self.civil_id})
			if employee_id:
				employee = frappe.get_doc('Employee', employee_id)
				self.employee_name = employee.employee_name
				self.gender = employee.gender
				self.nationality = employee.one_fm_nationality
				self.passport_expiry_date = employee.valid_upto
