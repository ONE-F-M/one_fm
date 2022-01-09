# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, getdate, get_url
from one_fm.utils import fetch_employee_signature

class RequestforPurchase(Document):
	def onload(self):
		self.set_onload('accepter', frappe.db.get_value('Purchase Settings', None, 'request_for_purchase_accepter'))
		self.set_onload('approver', frappe.db.get_value('Purchase Settings', None, 'request_for_purchase_approver'))
	
	def on_submit(self):
		self.notify_request_for_material_accepter()
		frappe.msgprint(_("Notification sent to purchaser"))
		
	@frappe.whitelist()
	def send_request_for_purchase(self):
		self.status = "Approved"
		self.save()
		self.reload()
		#self.notify_request_for_material_accepter()

	def notify_request_for_material_accepter(self):
		if self.accepter:
			page_link = get_url("/desk#Form/Request for Purchase/" + self.name)
			message = "<p>Please Review the Request for Purchase <a href='{0}'>{1}</a> Submitted by {2}.</p>".format(page_link, self.name, self.requested_by)
			subject = '{0} Request for Purchase by {1}'.format(self.status, self.requested_by)
			send_email(self, [self.accepter], message, subject)
			create_notification_log(subject, message, [self.accepter], self)
			# self.status = "Draft Request"
			self.save()
			self.reload()

	@frappe.whitelist()
	def make_purchase_order_for_quotation(self):
		if self.items_to_order:
			for item in self.items_to_order:
				create_purchase_order(supplier=item.supplier, request_for_purchase=self.name, item_code=item.item_code,
					qty=item.qty, rate=item.rate, delivery_date=item.delivery_date, uom=item.uom, description=item.description,
					warehouse=self.warehouse, quotation=item.quotation)
	
	@frappe.whitelist()
	def accept_approve_reject_request_for_purchase(self, status, approver, accepter, reason_for_rejection=None):
		page_link = get_url("/desk#Form/Request for Purchase/" + self.name)
		# Notify Requester
		self.notify_requester_accepter(page_link, status, [self.requested_by], reason_for_rejection)

		# Notify Approver
		if status == 'Accepted' and frappe.session.user == accepter:
			message = "<p>Please Review and Approve or Reject the Request for Purchase <a href='{0}'>{1}</a>, Accepted by {2}</p>".format(page_link, self.name, frappe.session.user)
			subject = '{0} Request for Purchase by {1}'.format(status, frappe.session.user)
			send_email(self, [approver], message, subject)
			create_notification_log(subject, message, [approver], self)

		#fetch Signature from employee doc using user ID
		if status == "Approved" and frappe.session.user == accepter:
			signature = fetch_employee_signature(accepter)
			if signature:
				self.authorized_signatures = signature
				self.save(ignore_permissions=True)
			else:
				frappe.msgprint(_("Your Signature is missing!"))

		# Notify Accepter
		if status in ['Approved', 'Rejected'] and frappe.session.user == approver:
			self.notify_requester_accepter(page_link, status, [accepter], reason_for_rejection)

		self.status = status
		self.reason_for_rejection = reason_for_rejection
		self.save()
		self.reload()

	def notify_requester_accepter(self, page_link, status, recipients, reason_for_rejection=None):
		message = "Request for Purchase <a href='{0}'>{1}</a> is {2} by {3}".format(page_link, self.name, status, frappe.session.user)
		if status == 'Rejected' and reason_for_rejection:
			message += " due to {0}".format(reason_for_rejection)
		subject = '{0} Request for Purchase by {1}'.format(status, frappe.session.user)
		send_email(self, recipients, message, subject)
		create_notification_log(subject, message, recipients, self)

def send_email(doc, recipients, message, subject):
	if 'Administrator' in recipients:
		recipients.remove('Administrator')
	if recipients and len(recipients) > 0:
		frappe.sendmail(
			recipients= recipients,
			subject=subject,
			message=message,
			reference_doctype=doc.doctype,
			reference_name=doc.name
		)

def create_notification_log(subject, message, for_users, reference_doc):
	if 'Administrator' in for_users:
		for_users.remove('Administrator')
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
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Purchase", source_name, 	{
		"Request for Purchase": {
			"doctype": "Request for Supplier Quotation",
			"field_map": [
				["name", "request_for_purchase"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Purchase Item": {
			"doctype": "Request for Supplier Quotation Item",
			"field_map": [
				["uom", "uom"]
			]
		}
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_quotation_comparison_sheet(source_name, target_doc=None):
	doclist = get_mapped_doc("Request for Purchase", source_name, 	{
		"Request for Purchase": {
			"doctype": "Quotation Comparison Sheet",
			"field_map": [
				["name", "request_for_purchase"]
			],
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Request for Purchase Item": {
			"doctype": "Quotation Comparison Sheet Item"
		}
	}, target_doc)
	rfq = frappe.db.get_value('Request for Supplier Quotation', {'request_for_purchase': doclist.request_for_purchase}, 'name')
	doclist.request_for_quotation = rfq if rfq else ''
	return doclist

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = obj.qty # flt(obj.qty) * flt(obj.conversion_factor)

	doclist = get_mapped_doc("Request for Purchase", source_name,		{
		"Request for Purchase": {
			"doctype": "Purchase Order",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Request for Purchase Quotation Item": {
			"doctype": "Purchase Order Item",
			"field_map": [
				["quotation_item", "supplier_quotation_item"],
				["quotation", "supplier_quotation"],
				["request_for_material", "request_for_material"],
				["request_for_material_item", "request_for_material_item"],
				["sales_order", "sales_order"]
			],
			"postprocess": update_item
		}
	}, target_doc, set_missing_values)

	return doclist

def create_purchase_order(**args):
	args = frappe._dict(args)
	po_id = frappe.db.exists('Purchase Order',
		{'one_fm_request_for_purchase': args.request_for_purchase, 'docstatus': ['<', 2], 'supplier': args.supplier}
	)
	if po_id:
		po = frappe.get_doc('Purchase Order', po_id)
	else:
		po = frappe.new_doc("Purchase Order")
		po.transaction_date = nowdate()
		po.set_warehouse = args.warehouse
		po.quotation = args.quotation
		# po.schedule_date = add_days(nowdate(), 1)
		# po.company = args.company
		po.supplier = args.supplier
		po.is_subcontracted = args.is_subcontracted or "No"
		# po.currency = args.currency or frappe.get_cached_value('Company',  po.company,  "default_currency")
		po.conversion_factor = args.conversion_factor or 1
		po.supplier_warehouse = args.supplier_warehouse or None
		po.one_fm_request_for_purchase = args.request_for_purchase

	po.append("items", {
		"item_code": args.item_code,
		"item_name": args.item_name,
		"description": args.description,
		"uom": args.uom,
		"qty": args.qty,
		"rate": args.rate,
		"schedule_date": getdate(args.delivery_date) if (args.delivery_date and getdate(nowdate()) < getdate(args.delivery_date)) else getdate(nowdate()),
		"expected_delivery_date": args.delivery_date
	})
	if not args.do_not_save:
		po.save(ignore_permissions=True)
		# if not args.do_not_submit:
		# 	po.submit()

	return po
