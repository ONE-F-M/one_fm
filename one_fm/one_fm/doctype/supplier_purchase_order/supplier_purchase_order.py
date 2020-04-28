# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from num2words import num2words
from one_fm.data import money_in_words

class SupplierPurchaseOrder(Document):
    def get_total_in_words(self):
        return money_in_words(self.total_amount)

    def on_submit(self):
        self.make_stock_entry()

    def make_stock_entry(self):
        doc = frappe.new_doc("Stock Entry")
        doc.stock_entry_type = 'Material Receipt'

        for item in self.items:
            doc.append("items", {
                "t_warehouse": self.place_of_delivery,
                "item_code": item.item_code,
                "description": item.description,
                "qty": item.qty,
                "uom": item.uom,
                "basic_rate": item.unit_price
            })
        doc.docstatus = 1
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)






    def get_signatures(self,employee_name):
        employee_signature = frappe.db.sql("select signature from `tabEmployee` where name='{0}'".format(employee_name))
        
        if(employee_signature):
            return employee_signature[0][0]


