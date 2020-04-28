# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, cint
from frappe.core.doctype.communication.email import make


class RequestforSupplierQuotation(Document):
    def validate(self):
        self.validate_duplicate_supplier()
        self.update_email_id()

    def validate_duplicate_supplier(self):
        supplier_list = [d.supplier for d in self.suppliers]
        if len(supplier_list) != len(set(supplier_list)):
            frappe.throw(_("Same supplier has been entered multiple times"))

    def update_email_id(self):
        for rfq_supplier in self.suppliers:
            if not rfq_supplier.email_id:
                rfq_supplier.email_id = frappe.db.get_value("Contact", rfq_supplier.contact, "email_id")

    def on_submit(self):
        frappe.db.set(self, 'status', 'Submitted')
        for supplier in self.suppliers:
            supplier.email_sent = 0

    def on_cancel(self):
        frappe.db.set(self, 'status', 'Cancelled')


    def get_supplier_group_list(self,supplier_group):
        supplier_group_list = frappe.db.sql("select parent from `tabSupplier Group Table` where parenttype='Supplier' and subgroup='{0}' order by parent".format(supplier_group),as_list=True)
        if supplier_group_list:
            return supplier_group_list
        else:
            return None


    def send_supplier_quotation_emails(self):
        for supplier in self.suppliers:
            if not supplier.email_id:
                frappe.throw(_("Row {0}: For supplier {0} Email Address is required to send email").format(supplier.idx, supplier.supplier))

            msg = frappe.render_template('one_fm/templates/emails/request_for_supplier_quotation.html', context={"items": self.items,"message_for_supplier": self.message_for_supplier,"terms": self.terms})

            sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None

            rec = supplier.email_id or None
            rec_cc = self.cc_email or None

            if rec != None and supplier.send_email:
                try:
                    frappe.sendmail(sender=sender, recipients= rec, cc= rec_cc,
                        content=msg, subject="Request for Quotation - {0}".format(self.name))
                    supplier.email_sent = 1
                    self.save()
                    frappe.msgprint(_("Email sent to supplier {0}").format(supplier.supplier))

                except:
                    frappe.msgprint(_("could not send"))


def get_supplier_contacts(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""select `tabContact`.name from `tabContact`, `tabDynamic Link`
        where `tabDynamic Link`.link_doctype = 'Supplier' and (`tabDynamic Link`.link_name=%(name)s
        and `tabDynamic Link`.link_name like %(txt)s) and `tabContact`.name = `tabDynamic Link`.parent
        limit %(start)s, %(page_len)s""", {"start": start, "page_len":page_len, "txt": "%%%s%%" % txt, "name": filters.get('supplier')})

