# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BugBusterReport(Document):
	def validate(self):
		# set employee
		if not self.bug_buster and frappe.session.user not in ['Administrator', 'administrator']:
			try:
				user_id, employee_name = frappe.db.get_values('Employee', {'user_id':frappe.session.user}, ['name', 'employee_name'], as_dict=1)[0].values()
			except:
				user_id, employee_name = '', ''
			self.bug_buster = user_id
			self.bug_buster_name = employee_name
