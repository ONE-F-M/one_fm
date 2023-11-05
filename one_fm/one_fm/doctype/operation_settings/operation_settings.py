# Copyright (c) 2023, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class OperationSettings(Document):
	def validate(self):
		if self.default_operation_manager:
			self.validate_operation_manager()

	def validate_operation_manager(self):
		'''
			Check if the user has "Operations Manager" role
		'''
		# Get all the roles associated with the operation manager user selected
		user_roles = frappe.get_roles(self.default_operation_manager)
		if not "Operations Manager" in user_roles:
			frappe.throw(_("The user {0} is not having 'Operations Manager' role".format(self.default_operation_manager)))
