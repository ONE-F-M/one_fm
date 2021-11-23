# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from one_fm.one_fm.payroll_utils import get_wage_for_employee_incentive


class EmployeeIncentiveTool(Document):
	@frappe.whitelist()
	def update_incentive_details(self):
		# This function used to update incentive details like wage and incentive amount in the tool
		if self.employee_incentives:
			for employee_incentive in self.employee_incentives:
				employee_incentive.wage_factor = self.wage_factor
				employee_incentive.salary_component = self.salary_component
				employee_incentive.payroll_date = self.payroll_date
				employee_incentive.wage = get_wage_for_employee_incentive(employee_incentive.employee, self.rewarded_by, self.payroll_date)
				employee_incentive.incentive_amount = get_incentive_amount(self.rewarded_by, self.wage_factor, employee_incentive.wage)

	@frappe.whitelist()
	def create_employee_incentive(self):
		# This function creates Employee Incentives from the tool
		if self.employee_incentives:
			number_of_incentive = 0
			for employee_incentive in self.employee_incentives:
				incentive=frappe.get_doc(dict(
					doctype='Employee Incentive',
					employee=employee_incentive.employee,
					rewarded_by=self.rewarded_by,
					wage_factor=employee_incentive.wage_factor,
					wage=employee_incentive.wage,
					incentive_amount=employee_incentive.incentive_amount,
					salary_component=employee_incentive.salary_component,
					payroll_date=employee_incentive.payroll_date
				))
				incentive.insert()
				number_of_incentive += 1
			self.reload()
			return number_of_incentive

def get_incentive_amount(rewarded_by, wage_factor, wage):
	'''
		This function returns incentive_amount
		if rewarded_by == "Number of Daily Wage" returns wage * wage_factor
		if rewarded_by == "Percentage of Monthly Wage" returns (wage * wage_factor / 100)

		args:
			rewarded_by: "Percentage of Monthly Wage" or "Number of Daily Wage"
			wage_factor: wage factor itself
			wage: wage will be Monthly wage or Daily wage based on rewarded_by value
	'''
	incentive_amount = wage * wage_factor
	if rewarded_by == 'Percentage of Monthly Wage':
		incentive_amount = incentive_amount / 100
	return incentive_amount

@frappe.whitelist()
def get_employees(department, branch = None, company = None):
	'''
		This function returns employee list
		department, branch and company are filters to get employee list
	'''
	filters = {"status": "Active", "department": department}
	for field, value in {'branch': branch, 'company': company}.items():
		if value:
			filters[field] = value

	return frappe.get_list("Employee", fields=["employee", "employee_name"], filters=filters, order_by="employee_name")
