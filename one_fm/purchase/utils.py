# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
import frappe, os
import json
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime
from datetime import tzinfo, timedelta, datetime
from dateutil import parser
from datetime import date
from frappe.model.naming import set_name_by_naming_series
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import expire_allocation, create_leave_ledger_entry
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate,get_first_day,get_last_day, today
import datetime

@frappe.whitelist()
def get_warehouse_contact_details(warehouse):
    from frappe.contacts.doctype.contact.contact import get_default_contact, get_contact_details
    contact = get_default_contact('Warehouse', warehouse)
    warehouse = frappe.get_doc('Warehouse', warehouse)
    location = ''
    contact_details = False
    if warehouse.address_line_1:
        location += warehouse.address_line_1+'\n'
    if warehouse.address_line_2:
        location += warehouse.address_line_2+'\n'
    if warehouse.city:
        location += warehouse.city+'\n'
    if warehouse.state:
        location += warehouse.state
    if contact:
        contact_details = get_contact_details(contact)
    return contact_details, location


@frappe.whitelist()
def make_material_delivery_note(source_name, target_doc=None):
    from frappe.model.mapper import get_mapped_doc
    doclist = get_mapped_doc("Purchase Receipt", source_name, 	{
        "Purchase Receipt": {
            "doctype": "Material Delivery Note",
            "field_map": [
                ["name", "purchase_receipt"]
            ],
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Purchase Receipt Item": {
            "doctype": "Material Delivery Note Item"
        }
    }, target_doc)

    po = False
    pr = frappe.get_doc('Purchase Receipt', doclist.purchase_receipt)
    for item in pr.items:
        if item.purchase_order:
            po = item.purchase_order
    if po:
        rfp = frappe.get_value('Purchase Order', po, 'one_fm_request_for_purchase')
        if rfp:
            rfm = frappe.get_value('Request for Purchase', rfp, 'request_for_material')
            doclist.request_for_material = rfm if rfm else ''
    return doclist

@frappe.whitelist()
def get_payment_details_for_po(po):
    mode_of_payment = False
    payment_amount = False
    purchase_order = frappe.get_doc('Purchase Order', po)
    payment = 'In Advance'
    query = """
        select
            pri.name
        from
            `tabPurchase Receipt Item` pri, `tabPurchase Receipt` pr
        where
            pr.name=pri.parent and pr.docstatus=1 and pri.purchase_order=%s
    """
    if frappe.db.sql(query, (po)):
        payment = 'On Delivery'
    if purchase_order.payment_schedule:
        for schedule in purchase_order.payment_schedule:
            if schedule.one_fm_payment == payment:
                mode_of_payment = schedule.mode_of_payment
                payment_amount = schedule.payment_amount
    return {'mode_of_payment':mode_of_payment, 'payment_amount':payment_amount}

def before_submit_purchase_receipt(doc, method):
    if not doc.one_fm_attach_delivery_note:
        frappe.throw(_('Please Attach Signed and Stamped Delivery Note'))

def filter_description_specific_for_item_group(doctype, txt, searchfield, start, page_len, filters):
    description_values = False
    query = "select name from `tab{0}` where"
    if filters.get("item_group") and filters.get("doctype") and frappe.db.has_column(filters.get("doctype"), 'item_group'):
        query += " item_group = %(item_group)s and"
    query += " name like %(txt)s limit %(start)s, %(page_len)s"
    description_values = frappe.db.sql(query.format(filters.get("doctype")),
        {'item_group': filters.get("item_group"), 'start': start, 'page_len': page_len, 'txt': "%%%s%%" % txt}
    )
    if description_values:
        return description_values
    else:
        query = "select name from `tab{0}` where item_group IS NULL and name like %(txt)s limit %(start)s, %(page_len)s"
        return frappe.db.sql(query.format(filters.get("doctype")),
            {'start': start, 'page_len': page_len, 'txt': "%%%s%%" % txt}
        )

@frappe.whitelist()
def check_for_signature_for_purchase_receipt(doc, method):
	if doc.status == "Completed":
		if not doc.authority_signature:
			frappe.throw(__('Please Sign the form to Accept the Request'))

@frappe.whitelist()
def check_for_signature_for_purchase_order(doc, method):
	if doc.workflow_state == "Approved":
		if not doc.authority_signature:
			frappe.throw(__('Please Sign the form to Accept the Request'))