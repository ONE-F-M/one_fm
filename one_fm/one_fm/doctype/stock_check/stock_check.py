# -*- coding: utf-8 -*-
# Copyright (c) 2019, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt

class StockCheck(Document):
	def set_actual_qty(self, item_code, warehouse):
		if item_code and warehouse:
			current_actual_qty = flt(0)
			actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
				where item_code = %s and warehouse = %s""", (item_code, warehouse))
			if actual_qty:
				current_actual_qty = flt(actual_qty[0][0])

		return current_actual_qty
