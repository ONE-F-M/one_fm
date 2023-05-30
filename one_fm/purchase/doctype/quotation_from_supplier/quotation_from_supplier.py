# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class QuotationFromSupplier(Document):
	def validate(self):
		if not self.items:
			self.set_items()
		self.validate_item_qty()
		self.set_totals()

	def validate_item_qty(self):
		# Get items qty is greater than the requested qty
		items = [item.idx for item in self.items if (item.qty_requested and item.qty_requested < item.qty)]
		if items and len(items) > 0:
			frappe.throw(_("Items are greater in quantity than requested in rows {0}".format(items)))

	def set_totals(self):
		if self.items:
			amount = 0
			qty = 0
			for item in self.items:
				amount += item.amount if item.amount else 0
				qty += item.qty if item.qty else 0
			self.total_qty = qty
			self.total = amount
			self.grand_total = amount

	def set_items(self):
		if self.request_for_quotation:
			rfq = frappe.get_doc('Request for Supplier Quotation', self.request_for_quotation)
			if rfq.items:
				for rfq_item in rfq.items:
					item = self.append('items')
					item.item_name = rfq_item.item_name
					item.description = rfq_item.description
					item.qty_requested = rfq_item.qty
					item.qty = rfq_item.qty
					item.uom = rfq_item.uom
					item.item_code = rfq_item.item_code
					item.warehouse = rfq_item.t_warehouse
