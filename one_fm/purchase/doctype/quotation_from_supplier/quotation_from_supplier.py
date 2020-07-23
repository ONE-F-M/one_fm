# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class QuotationFromSupplier(Document):
	def validate(self):
		self.set_totals()

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
