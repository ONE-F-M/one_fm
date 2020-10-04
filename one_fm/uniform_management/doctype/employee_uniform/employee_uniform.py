# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe import _

class EmployeeUniform(Document):
	def before_insert(self):
		if self.type == 'Return':
			self.naming_series = 'EUR-.YYYY.-'
		else:
			self.naming_series = 'EUI-.YYYY.-'

	def on_submit(self):
		if self.type == "Issue":
			self.status = 'Issued'
			self.issued_on = today()
		elif self.type == "Return":
			self.status = 'Returned'
			self.returned_on = today()

	def validate(self):
		if not self.uniforms:
			frappe.throw(_("Uniforms required in Employee Uniform"))
		self.validate_issue()
		self.validate_return()

	def validate_issue(self):
		self.validate_issued_items_are_returned()

	def validate_issued_items_are_returned(self):
		pass

	def validate_return(self):
		if self.type == 'Return' and not self.reason_for_return:
			frappe.throw(_("Reason for Return required in Employee Uniform"))
		self.validate_item_return_before_expiry()

	def validate_item_return_before_expiry(self):
		if self.type == 'Return' and self.reason_for_return in ['Item Damage', 'Item Expired']:
			pass

	def set_uniform_details(self):
		uniforms = False
		if self.employee:
			if self.type == "Issue" and self.designation:
				uniforms = get_project_uniform_details(self.designation, self.project)
				if not uniforms:
					frappe.msgprint(msg = 'No Designation Uniform Profile Found',
				       title = 'Warning',
				       indicator = 'red'
				    )
			elif self.type == "Return":
				uniforms = get_items_to_return(self.employee)

		if uniforms:
			for uniform in uniforms:
				unifrom_issue = self.append('uniforms')
				unifrom_issue.item = uniform.item
				unifrom_issue.item_name = uniform.item_name
				unifrom_issue.quantity = uniform.quantity
				unifrom_issue.qty_uom = uniform.uom

def get_project_uniform_details(designation_id, project_id=''):
	if frappe.db.get_value('Designation', designation_id, 'one_fm_is_uniform_needed_for_this_job'):
		filters = {'designation': designation_id, 'project': project_id}
		query = """
			select
				name
			from
				`tabDesignation Uniform Profile`
			where
				designation=%(designation)s {condition}
		"""

		condition = "and project IS NULL"
		if project_id:
			condition = "and project=%(project)s"

		profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
		if not profile_id and project_id:
			condition = "and project IS NULL"
			profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
		if profile_id and profile_id[0]['name']:
			profile = frappe.get_doc('Designation Uniform Profile', profile_id[0]['name'])
			return profile.uniforms if profile.uniforms else False
	return False

def get_items_to_return(employee_id):
	return get_issued_items(employee_id)

def get_issued_items(employee_id):
	return False
