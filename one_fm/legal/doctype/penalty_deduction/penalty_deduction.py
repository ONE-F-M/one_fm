# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import getdate

class PenaltyDeduction(Document):
	def on_submit(self):
		self.create_additional_salary()

	def create_additional_salary(self):
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.employee = self.employee
		additional_salary.salary_component = "Penalty"
		additional_salary.amount = self.deducted_amount
		additional_salary.payroll_date = getdate()
		additional_salary.company = erpnext.get_default_company()
		#additional_salary.company = "ONE Facilities Management"
		additional_salary.overwrite_salary_structure_amount = 1
		additional_salary.notes = "Penalty Deduction for Payroll Period: {start} to {end} including previous unsettled balance amount, if applicable.".format(start=self.from_date, end=self.to_date)
		additional_salary.insert()
		additional_salary.submit()
