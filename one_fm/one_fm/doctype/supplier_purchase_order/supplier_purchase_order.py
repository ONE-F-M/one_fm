# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from num2words import num2words
from one_fm.data import money_in_words
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate

class SupplierPurchaseOrder(Document):
    def get_total_in_words(self):
        return money_in_words(self.total_amount)

    def validate(self):
        self.validate_qty_amount()

    def on_submit(self):
        self.validate_selected_item()
        self.validate_completed_order()
        self.make_stock_entry()

    def on_update(self):
        if self.workflow_state == 'Approved by Financial':
            self.status = 'Waiting for management approval'
        elif self.workflow_state == 'Approved by Management':
            self.status = 'Approved and sent to supplier'

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

    def validate_qty_amount(self):
        for item in self.items:
            if cint(item.qty)>cint(item.remain_qty):
                frappe.throw("The Remaining qty needed from item <b>{0}</b> is: <b>{1}</b>".format(item.item_code, item.remain_qty))


    def validate_selected_item(self):
        for item in self.items:
            doc = frappe.get_doc("Purchase Request Item", item.purchase_request_item_id)
            doc.ordered_qty = cint(doc.ordered_qty)+cint(item.qty)

            if doc.selected==1:
                old_purchase_order = frappe.db.sql("""select parent from `tabSupplier Purchase Order Item` where parenttype='Supplier Purchase Order'
                                  and item_code='{0}' """.format(item.item_code))
                if old_purchase_order:
                    frappe.throw("Item <b>{0}</b> is already purchased, please check purchase order <b>{1}</b>".format(item.item_code,old_purchase_order[0][0]))
                else:
                    frappe.throw("Item <b>{0}</b> is already purchased !".format(item.item_code))

            elif doc.selected!=1 and cint(item.qty)-cint(item.remain_qty)==0:
                doc.selected = 1

            doc.flags.ignore_mandatory = True
            doc.save(ignore_permissions=True)
            frappe.db.commit()


    def validate_completed_order(self):
        purchase_request = frappe.get_doc("Purchase Request", self.purchase_request)
        items_status = []
        for item in purchase_request.items:
            items_status.append(item.selected)

        if 0 in items_status:
            purchase_request.ordered = 0
        else:
            purchase_request.ordered = 1
        purchase_request.flags.ignore_mandatory = True
        purchase_request.save(ignore_permissions=True)
        frappe.db.commit()



    def get_signatures(self,employee_name):
        employee_signature = frappe.db.sql("select signature from `tabEmployee` where name='{0}'".format(employee_name))
        
        if(employee_signature):
            return employee_signature[0][0]


