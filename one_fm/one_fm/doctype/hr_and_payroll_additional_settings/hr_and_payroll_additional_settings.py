# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class HRandPayrollAdditionalSettings(Document):
	@frappe.whitelist()
	def get_projects_not_set_in_payroll_cycle_but_assigned_in_employee(self):
		project_list = ', '.join(['"{}"'.format(payroll_cycle.project) for payroll_cycle in self.project_payroll_cycle])
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
		return frappe.db.sql(query.format(project_list))
