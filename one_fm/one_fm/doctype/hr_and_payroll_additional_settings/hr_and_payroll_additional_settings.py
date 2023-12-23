# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class HRandPayrollAdditionalSettings(Document):
	@frappe.whitelist()
	def get_projects_not_configured_in_payroll_cycle_but_linked_in_employee(self):
		project_list = ', '.join(['"{}"'.format(payroll_cycle.project) for payroll_cycle in self.project_payroll_cycle])
		if not project_list:
			project_list = "''"
		return get_projects_not_configured_in_payroll_cycle_but_linked_in_employee(project_list)

def get_projects_not_configured_in_payroll_cycle_but_linked_in_employee(project_list):
	'''
		Method to get list of projects not set in payroll cycle but linked in employee
		args:
			project_list: list of projects in text format(Example: ("Project1", "Project2"))
		return:
			projects list
	'''
	query = '''
		select
			distinct project
		from
			tabEmployee
		where
			status = "Active"
			and
			project NOT IN ({0})
	'''
	return frappe.db.sql(query.format(project_list), as_dict=True)

def get_projects_configured_in_payroll_cycle(payroll_start_day):
	query = '''
		select
			project
		from
			`tabProject Payroll Cycle`
		where
			payroll_start_day = '{0}'
	'''
	projects = frappe.db.sql(query.format(payroll_start_day), as_dict=True)
	return ', '.join(['"{}"'.format(project.project) for project in projects])
