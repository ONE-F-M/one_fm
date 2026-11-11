# Copyright (c) 2023, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint

class OperationSettings(Document):
	def validate(self):
		if self.default_operation_manager:
			self.validate_operation_manager()
		if self.operation_admin:
			self.validate_operation_admin()
		self.validate_subcontractor_attendance_start_day()

	def validate_subcontractor_attendance_start_day(self):
		'''
			The start day must be 1 to 28 so that it exists in every month (including February)
		'''
		start_day = cint(self.subcontractor_attendance_submission_start_day)
		if start_day < 1 or start_day > 28:
			frappe.throw(_("Subcontractor Attendance Submission Start Day must be between 1 and 28."))

	def validate_operation_manager(self):
		'''
			Check if the user has "Operations Manager" role
		'''
		# Get all the roles associated with the operation manager user selected
		user_roles = frappe.get_roles(self.default_operation_manager)
		if not "Operations Manager" in user_roles:
			frappe.throw(_("The user {0} is not having 'Operations Manager' role".format(self.default_operation_manager)))

	def validate_operation_admin(self):
		'''
			Check if the selected Operation Admin user has the "Operations Admin" role
		'''
		# Get all the roles associated with the operation admin user selected
		user_roles = frappe.get_roles(self.operation_admin)
		if not "Operation Admin" in user_roles:
			frappe.throw(_("The user {0} is not having 'Operation Admin' role").format(self.operation_admin))
