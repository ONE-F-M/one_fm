# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_years

class MedicalInsurance(Document):
	def validate(self):
		self.valid_work_permit_exists()
		self.update_end_date()

	def update_end_date(self):
		if self.category == 'Individual' and self.no_of_years and self.no_of_years > 0 and self.start_date:
			self.end_date = add_years(self.start_date, self.no_of_years)
		elif self.category == 'Group':
			for item in self.items:
				if item.no_of_years and item.no_of_years > 0 and item.start_date:
					item.end_date = add_years(item.start_date, item.no_of_years)

	def valid_work_permit_exists(self):
		# TODO: Check valid work permit exists for the employee
		pass

@frappe.whitelist()
def get_employee_data_from_civil_id(civil_id):
	employee_id = frappe.db.exists('Employee', {'one_fm_civil_id': civil_id})
	if employee_id:
		return frappe.get_doc('Employee', employee_id)
