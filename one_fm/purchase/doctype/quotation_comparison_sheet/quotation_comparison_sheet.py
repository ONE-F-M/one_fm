# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber, Anthony Emmanuel and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class QuotationComparisonSheet(Document):
	def on_submit(self):
		update_request_for_purchase(self)

	@frappe.whitelist()
	def get_rfq(self, rfq, rfm):
		return {
			'rfq': frappe.get_doc('Request for Supplier Quotation', rfq),
			'rfm': frappe.get_doc('Request for Material', rfm)
		}

	@frappe.whitelist()
	def create_purchase_order(self, **kwargs):
		# create purchase receipt
		rfm = frappe.get_doc('Request for Material', self.request_for_material)
		item_codes = {}
		for i in rfm.items:
			item_codes[i.requested_item_name] = i.item_code;
		# sort suppliers
		suppliers = {}
		for i in self.items:
			if(suppliers.get(i.supplier)):
				suppliers[i.supplier].append(i)
			else:
				suppliers[i.supplier] = [i]

		# create purchase order
		for supplier, items in suppliers.items():
			po_items = []
			for i in items:
				po_items.append({
					'item_code': item_codes[i.item_name],
					'schedule_date': i.schedule_date,
					'qty': i.qty,
					'rate': i.rate,
					'schedule_date':'2022-02-23',
				})
			doc = frappe.get_doc({
				'doctype':'Purchase Order',
				'supplier':supplier,
				'one_fm_request_for_purchase':self.request_for_purchase,
				'request_for_material':self.request_for_material,
				'schedule_date': rfm.schedule_date,
				'set_warehouse': rfm.t_warehouse,
				'items': po_items
			}).insert()
		frappe.msgprint(_('PO creation complete'));
		return


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
def get_quotation_against_rfq(rfq):
	quotation_list = frappe.get_list('Quotation From Supplier', {'request_for_quotation': rfq})
	quotations = []
	for quotation in quotation_list:
		quotations.append(frappe.get_doc('Quotation From Supplier', quotation.name))
	return quotations
