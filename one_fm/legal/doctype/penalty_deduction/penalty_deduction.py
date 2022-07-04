# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe.utils import getdate, cint
from datetime import datetime
import datetime


class PenaltyDeduction(Document):
	def on_submit(self):
		self.create_additional_salary()

	def create_additional_salary(self):
		if frappe.db.get_single_value('HR and Payroll Additional Settings', 'payroll_date'):
			date = frappe.db.get_single_value('HR and Payroll Additional Settings', 'payroll_date')
			year = getdate().year - 1 if getdate().day < cint(date) and  getdate().month == 1 else getdate().year
			month = getdate().month if getdate().day >= cint(date) else getdate().month - 1

			#calculate Payroll date, start and end date.
			payroll_date = datetime.datetime(year, month, cint(date)-1).strftime("%Y-%m-%d")	
				
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.employee = self.employee
		additional_salary.salary_component = "Penalty"
		additional_salary.amount = self.deducted_amount
		additional_salary.payroll_date = payroll_date if payroll_date else getdate()
		additional_salary.company = erpnext.get_default_company()
		additional_salary.overwrite_salary_structure_amount = 1
		additional_salary.notes = "Penalty Deduction for Payroll Period: {start} to {end} including previous unsettled balance amount, if applicable.".format(start=self.from_date, end=self.to_date)
		additional_salary.insert()
		additional_salary.submit()
