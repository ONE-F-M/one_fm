# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
from frappe import _

class RequestforMaterial(Document):
	def validate(self):
		self.set_title()
		self.validate_details_against_type()

	def validate_details_against_type(self):
		if self.type:
			if self.type == 'Individual':
				self.project = ''
				self.project_details = ''
			if self.type == 'Project Mobilization':
				self.employee = ''
				self.employee_name = ''
				self.department = ''

	def set_title(self):
		'''Set title as comma separated list of items'''
		# if not self.title:
		items = ', '.join([d.item_name for d in self.items][:3])
		self.title = _('Material Request for {0}').format(items)[:100]

	def on_update_after_submit(self):
		from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError, remove as remove_assignment
		if self.technical_verification_needed == 'Yes' and self.technical_verification_from and not self.technical_remarks:
			try:
				add_assignment({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': self.technical_verification_from,
					'description': _('Please add Your Technical Remarks for the Item Descriptions')
				})
				self.add_comment("Comment", _("Waiting for Technical Verification"))
			except DuplicateToDoError:
				frappe.message_log.pop()
				pass
		elif self.technical_verification_needed == "No" and self.technical_verification_from:
			remove_assignment(self.doctype, self.name, self.technical_verification_from)

	def check_modified_date(self):
		mod_db = frappe.db.sql("""select modified from `tabRequest for Material` where name = %s""",
			self.name)
		date_diff = frappe.db.sql("""select TIMEDIFF('%s', '%s')"""
			% (mod_db[0][0], cstr(self.modified)))

		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(_(self.doctype), self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.status_can_change(status)
		# self.set_status(update=True, status=status)
		self.db_set('status', status)

	def status_can_change(self, status):
		"""
		validates that `status` is acceptable for the present controller status
		and throws an Exception if otherwise.
		"""
		if self.status and self.status == 'Cancelled':
			# cancelled documents cannot change
			if status != self.status:
				frappe.throw(
					_("{0} {1} is cancelled so the action cannot be completed").
						format(_(self.doctype), self.name),
					frappe.InvalidStatusError
				)

		elif self.status and self.status == 'Draft':
			# draft document to pending only
			if status != 'Pending':
				frappe.throw(
					_("{0} {1} has not been submitted so the action cannot be completed").
						format(_(self.doctype), self.name),
					frappe.InvalidStatusError
				)

@frappe.whitelist()
def update_status(name, status):
	request_for_material = frappe.get_doc('Request for Material', name)
	request_for_material.check_permission('write')
	request_for_material.update_status(status)

@frappe.whitelist()
def make_stock_entry(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor \
			if flt(obj.stock_qty) > flt(obj.ordered_qty) else 0
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		target.t_warehouse = obj.warehouse

	def set_missing_values(source, target):
		target.purpose = 'Material Transfer'
		target.run_method("calculate_rate_and_amount")
		target.set_stock_entry_type()
		target.set_job_card_data()

	doclist = get_mapped_doc("Request for Material", source_name, {
		"Request for Material": {
			"doctype": "Stock Entry",
			"field_map": [
				["name", "one_fm_request_for_material"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Stock Entry Detail",
			"field_map": {
				"uom": "stock_uom",
				"name": "one_fm_request_for_material_item",
				"parent": "one_fm_request_for_material"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.item_code
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Material", source_name, 	{
		"Request for Material": {
			"doctype": "Request for Supplier Quotation",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Request for Supplier Quotation Item",
			"field_map": [
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			],
			"condition": lambda doc: not doc.item_code
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_request_for_purchase(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Material", source_name, 	{
		"Request for Material": {
			"doctype": "Request for Purchase",
			"field_map": [
				["name", "request_for_material"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Request for Purchase Item",
			"field_map": [
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			]
		}
	}, target_doc)

	return doclist
