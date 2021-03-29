# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, get_url
from frappe import _
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission

class RequestforMaterial(Document):
	def on_submit(self):
		pass
		# self.notify_request_for_material_accepter()
		#self.notify_request_for_material_approver()

	def notify_request_for_material_accepter(self):
		if self.request_for_material_accepter:
			page_link = get_url("/desk#Form/Request for Material/" + self.name)
			message = "<p>Please Review and Accept or Reject the Request for Material <a href='{0}'>{1}</a> Submitted by {2}.</p>".format(page_link, self.name, self.requested_by)
			subject = '{0} Request for Material by {1}'.format(self.status, self.requested_by)
			send_email(self, [self.request_for_material_accepter], message, subject)
			create_notification_log(subject, message, [self.request_for_material_accepter], self)

	def notify_request_for_material_approver(self):
		if self.request_for_material_approver:
			page_link = get_url("/desk#Form/Request for Material/" + self.name)
			message = "<p>Please Review and Approve or Reject the Request for Material <a href='{0}'>{1}</a> Submitted by {2}.</p>".format(page_link, self.name, self.requested_by)
			subject = '{0} Request for Material by {1}'.format(self.status, self.requested_by)
			send_email(self, [self.request_for_material_approver], message, subject)
			create_notification_log(subject, message, [self.request_for_material_approver], self)

	def accept_approve_reject_request_for_material(self, status, reason_for_rejection=None):
		if frappe.session.user in [self.request_for_material_accepter, self.request_for_material_approver]:
			page_link = get_url("/desk#Form/Request for Material/" + self.name)
			# Notify Requester
			#self.notify_requester_accepter(page_link, status, [self.requested_by], reason_for_rejection)

			# Notify Approver
			if status == 'Accepted' and frappe.session.user == self.request_for_material_accepter and self.request_for_material_approver:
				message = "<p>Please Review and Approve or Reject the Request for Material <a href='{0}'>{1}</a>, Accepted by {2}</p>".format(page_link, self.name, frappe.session.user)
				subject = '{0} Request for Material by {1}'.format(status, frappe.session.user)
				send_email(self, [self.request_for_material_approver], message, subject)
				create_notification_log(subject, message, [self.request_for_material_approver], self)

			# Notify Accepter
			if status in ['Approved', 'Rejected'] and frappe.session.user == self.request_for_material_approver and self.request_for_material_accepter:
				pass
				#self.notify_requester_accepter(page_link, status, [self.request_for_material_accepter], reason_for_rejection)

			self.status = status
			if status == "Approved":
				# Notify Stock Manager - Stock Manger Check If Item Available
				# If Item Available then Create SE Issue and Transfer and update qty issued in the RFMItem
				# If Qty - qty Issued > 0 then Create RFP button appear
				users = get_users_with_role('Stock Manager')
				filtered_users = []
				for user in users:
					if has_permission(doctype=self.doctype, user=user):
						filtered_users.append(user)
				if filtered_users and len(filtered_users) > 0:
					self.notify_requester_accepter(page_link, status, filtered_users)

			self.reason_for_rejection = reason_for_rejection
			self.save()
			self.reload()

	def notify_requester_accepter(self, page_link, status, recipients, reason_for_rejection=None):
		message = "Request for Material <a href='{0}'>{1}</a> is {2} by {3}".format(page_link, self.name, status, frappe.session.user)
		if status == 'Rejected' and reason_for_rejection:
			message += " due to {0}".format(reason_for_rejection)
		subject = '{0} Request for Material by {1}'.format(status, frappe.session.user)
		send_email(self, recipients, message, subject)
		create_notification_log(subject, message, recipients, self)

	def validate(self):
		self.validate_details_against_type()
		self.set_request_for_material_accepter_and_approver()
		self.set_item_fields()
		self.set_title()

	def set_item_fields(self):
		if self.items and self.type == 'Stock':
			for item in self.items:
				item.requested_item_name = item.item_name
				item.requested_description = item.description

	def set_request_for_material_accepter_and_approver(self):
		if not self.request_for_material_accepter:
			self.request_for_material_accepter = frappe.db.get_value('Purchase Settings', None, 'request_for_material_accepter')
		if not self.request_for_material_approver:
			self.request_for_material_approver = frappe.db.get_value('Purchase Settings', None, 'request_for_material_approver')

	def validate_details_against_type(self):
		if self.type:
			if self.type == 'Individual':
				self.project = ''
				self.project_details = ''
			if self.type == 'Project Mobilization':
				self.employee = ''
				self.employee_name = ''
				self.department = ''
			if self.type == 'Project':
				self.employee = ''
				self.employee_name = ''
				self.department = ''

	def set_title(self):
		'''Set title as comma separated list of items'''
		# if not self.title:
		items = ', '.join([d.requested_item_name for d in self.items][:3])
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

def send_email(doc, recipients, message, subject):
	frappe.sendmail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def create_notification_log(subject, message, for_users, reference_doc):
	for user in for_users:
		doc = frappe.new_doc('Notification Log')
		doc.subject = subject
		doc.email_content = message
		doc.for_user = user
		doc.document_type = reference_doc.doctype
		doc.document_name = reference_doc.name
		doc.from_user = reference_doc.modified_by
		doc.insert(ignore_permissions=True)
@frappe.whitelist()
def bring_designation_items(designation):
	designation_doc = frappe.get_doc('Designation Profile', designation)
	item_list = []
	if designation_doc != null:
		for item in designation_doc.get("uniforms"):
			item_list.append({
				'item':item.item,
				'item_name':item.item_name,
				'quantity':item.quantity,
				'uom':item.uom
			})
		for item in designation_doc.get("accommodation_assets"):
			item_list.append({
				'item':item.item,
				'item_name':item.item_name,
				'quantity':item.quantity,
				'uom':item.uom
			})
		for item in designation_doc.get("accommodation_consumables"):
			item_list.append({
				'item':item.item,
				'item_name':item.item_name,
				'quantity':item.quantity,
				'uom':item.uom
			})
	else:
		frappe.throw(_("No profile found for {}").format(designation))
	return {'item_list': item_list}

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
def make_sales_invoice(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty))/ target.conversion_factor \
			if flt(obj.stock_qty) > flt(obj.ordered_qty) else 0
		target.qty = qty
		target.transfer_qty = qty * obj.conversion_factor
		target.conversion_factor = obj.conversion_factor

		# target.t_warehouse = obj.warehouse

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	doclist = get_mapped_doc("Request for Material", source_name, {
		"Request for Material": {
			"doctype": "Sales Invoice",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"uom": "stock_uom"
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
def make_delivery_note(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Material", source_name, 	{
		"Request for Material": {
			"doctype": "Delivery Note",			
			"field_map": [
				["name", "request_for_material"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Material Item": {
			"doctype": "Delivery Note Item",
			"field_map": [
				["requested_description", "description"],
				["requested_item_name", "item_name"],
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			]
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
				["requested_description", "description"],
				["requested_item_name", "item_name"],
				["name", "request_for_material_item"],
				["parent", "request_for_material"]
			]
		}
	}, target_doc)

	return doclist
