# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PurchaseRequest(Document):

    # def validate(self):
    #     selected_suppliers = []
    #     linked_suppliers = []

    #     for existed_supplier in self.items:
    #         linked_suppliers.append(existed_supplier.supplier)

    #     for supp in self.suppliers_quotation:
    #         if supp.approved:
    #             selected_suppliers.append(supp.supplier)

    #     for supplier in selected_suppliers:
    #         doc = frappe.new_doc("Purchase Order")
    #         doc.supplier = supplier

    #         for i in self.items:
    #             if supplier==i.supplier:
    #                 doc.append("items", {
    #                     "item_code": i.item_code,
    #                     "schedule_date": i.reqd_by_date,
    #                     "description": i.description,
    #                     "qty": float(i.requested_quantity),
    #                     "uom": i.uom,
    #                     "rate": i.unit_price,
    #                     "project": self.code
    #                 })

    #         if supplier in linked_suppliers:
    #             doc.flags.ignore_mandatory = True
    #             doc.insert(ignore_permissions=True)



        # frappe.get_doc({
        #     "doctype": "Project Planning",
        #     "project_name": self.project_name
        # }).save(ignore_permissions = True)

        # frappe.db.commit()

        # pp = frappe.get_value("Project Planning", filters = {"project_name": self.project_name}, fieldname = "name")

        # frappe.msgprint(_("""Project Planning have been created: <b><a href="#Form/Project Planning/{pp}">{pp}</a></b>""".format(pp = pp)))


    def get_signatures(self,employee_name):
        employee_signature = frappe.db.sql("select signature from `tabEmployee` where name='{0}'".format(employee_name))
        
        if(employee_signature):
            return employee_signature[0][0]

