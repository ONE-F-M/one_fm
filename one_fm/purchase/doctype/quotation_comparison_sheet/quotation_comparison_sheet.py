# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class QuotationComparisonSheet(Document):
	def on_submit(self):
		update_request_for_purchase(self)

def update_request_for_purchase(doc):
	if doc.items:
		rfp = frappe.get_doc('Request for Purchase', doc.request_for_purchase)
		for item in doc.items:
			items_to_order = rfp.append('items_to_order')
			items_to_order.item_name = item.item_name
			items_to_order.description = item.description
			items_to_order.uom = item.uom
			items_to_order.qty = item.qty
			items_to_order.quotation = item.quotation
			items_to_order.quotation_item = item.quotation_item
			items_to_order.rate = frappe.db.get_value('Quotation From Supplier Item', item.quotation_item, 'rate')
			items_to_order.delivery_date = frappe.db.get_value('Quotation From Supplier', item.quotation, 'estimated_delivery_date')
		rfp.save(ignore_permissions = True)

	@frappe.whitelist()
	def get_suppliers(self, suppliers):
		# return frappe.get_doc('Request for Supplier Quotation', rfsq)

		return
@frappe.whitelist()
def get_quotation_against_rfq(rfq):
	quotation_list = frappe.get_list('Quotation From Supplier', {'request_for_quotation': rfq})
	quotations = []
	for quotation in quotation_list:
		quotations.append(frappe.get_doc('Quotation From Supplier', quotation.name))
	return quotations
