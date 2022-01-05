# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, cint
from frappe.core.doctype.communication.email import make
from erpnext.accounts.party import get_party_account_currency, get_party_details
from six import string_types


class RequestforSupplierQuotation(Document):
    def validate(self):
        if hasattr(self,"workflow_state"):
            if "Rejected" in self.workflow_state:
                self.docstatus = 1
                self.docstatus = 2

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

    @frappe.whitelist()
    def create_quotation_from_supplier(self):
        quotation = frappe.new_doc('Quotation From Supplier')
        quotation.request_for_quotation = self.name
        quotation.request_for_purchase = self.request_for_purchase
        if self.items:
            for rfq_item in self.items:
                item = quotation.append('items')
                item.item_name = rfq_item.item_name
                item.description = rfq_item.description
                item.qty = rfq_item.qty
                item.uom = rfq_item.uom
                item.stock_uom = rfq_item.uom
        return quotation.as_dict()

    def get_supplier_group_list(self,supplier_group):
        supplier_group_list = frappe.db.sql("select parent from `tabSupplier Group Table` where parenttype='Supplier' and subgroup='{0}' order by parent".format(supplier_group),as_list=True)
        if supplier_group_list:
            return supplier_group_list
        else:
            return None

    def get_link(self):
        # RFQ link for supplier portal
        return get_url("/rfq1/" + self.name)

    def send_supplier_quotation_emails(self):
        for supplier in self.suppliers:
            if not supplier.email_id:
                frappe.throw(_("Row {0}: For supplier {0} Email Address is required to send email").format(supplier.idx, supplier.supplier))

            msg = frappe.render_template('one_fm/templates/emails/request_for_supplier_quotation.html',
                context={"items": self.items,"message_for_supplier": self.message_for_supplier,"terms": self.terms, "rfq_link": self.get_link()})

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

def get_list_context(context=None):
	from one_fm.templates.pages.controllers.website_list import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Request for Supplier Quotation'),
	})
	return list_context

# This method is used to make supplier quotation from supplier's portal.
@frappe.whitelist()
def create_supplier_quotation(doc, files=None):
    if isinstance(doc, string_types):
        doc = json.loads(doc)

    # try:
    sq_doc = frappe.get_doc({
    "doctype": "Quotation From Supplier",
    "supplier": doc.get('supplier'),
    "terms": doc.get("terms"),
    "company": doc.get("company"),
    "currency": doc.get('currency') or get_party_account_currency('Supplier', doc.get('supplier'), doc.get('company')),
    "buying_price_list": doc.get('buying_price_list') or frappe.db.get_value('Buying Settings', None, 'buying_price_list')
    })
    add_items(sq_doc, doc.get('supplier'), doc.get('items'))
    sq_doc.flags.ignore_permissions = True
    sq_doc.run_method("set_missing_values")
    sq_doc.save()
    if files:
        files_json = json.loads(files)
        files_obj = frappe._dict(files_json)
        for file in files_obj:
            attach_file_to_sq(files_obj[file]['files_data'], sq_doc)
        sq_doc.save(ignore_permissions=True)
    frappe.msgprint(_("Quotation From Supplier {0} created").format(sq_doc.name))
    return sq_doc.name
    # except Exception:
    # return None

@frappe.whitelist()
def attach_file_to_sq(filedata, sq_doc):
    from frappe.utils.file_manager import save_file
    if filedata:
        for fd in filedata:
            filedoc = save_file(fd["filename"], fd["dataurl"], "Quotation From Supplier", sq_doc.name, decode=True, is_private=0)
            sq_doc.attach_sq = filedoc.file_url

def add_items(sq_doc, supplier, items):
	for data in items:
		if data.get("qty") > 0:
			if isinstance(data, dict):
				data = frappe._dict(data)

			create_rfq_items(sq_doc, supplier, data)

def create_rfq_items(sq_doc, supplier, data):
	sq_doc.append('items', {
		"item_code": data.item_code,
		"item_name": data.item_name,
		"description": data.description,
		"qty": data.qty,
        "uom": "PCS",
		"rate": data.rate,
        "amount": data.amount,
		"supplier_part_no": frappe.db.get_value("Item Supplier", {'parent': data.item_code, 'supplier': supplier}, "supplier_part_no"),
		"warehouse": data.warehouse or '',
		"request_for_quotation_item": data.name,
		"request_for_quotation": data.parent
	})
