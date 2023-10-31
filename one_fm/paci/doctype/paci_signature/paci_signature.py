# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PACISignature(Document):
	def before_insert(self):
		if not self.session_employee:
			session_employee = frappe.cache().get_value(frappe.session.user).employee
			if not session_employee:
				session_employee = frappe.db.get_value('Employee', {'user_id':frappe.session.user }, 'name')
			self.session_employee = session_employee
