# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
import frappe, os
from one_fm.purchase.doctype.request_for_purchase.request_for_purchase  import get_users_with_role
import json
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime
from datetime import tzinfo, timedelta, datetime
from dateutil import parser
from datetime import date
from frappe.model.naming import set_name_by_naming_series
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import expire_allocation, create_leave_ledger_entry
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate,get_first_day,get_last_day, today
import time
import math, random
import hashlib
from one_fm.api.notification import create_notification_log
from one_fm.utils import fetch_employee_signature
from one_fm.utils import (workflow_approve_reject, send_workflow_action_email)
from one_fm.api.doc_events import get_employee_user_id

from frappe.desk.form.assign_to import  remove as remove_assignment
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

def get_approving_user(doc):
    """
        Fetch the line manager of the user that created the request for material
    """
    if doc.get('request_for_material'):
        return frappe.get_value("Request for Material", doc.get('request_for_material'), 'request_for_material_approver')

def set_po_approver(doc,ev):
    """
    Fetch the line manager of the user that created the request for material
    if no request for material is found, the Request for Purchase.


    Args:
        doc (doctype): valid doctype
    """
    if not doc.department_manager:
        doc.department_manager = get_approving_user(doc)

def validate_purchase_item_uom(doc,method):
    check_list = []
    for d in doc.get("items"):
        if d.qty:
            default_qty = frappe.get_value("UOM Conversion Detail", {'parent':d.item_code, 'uom':d.uom}, ['conversion_factor'])
            if d.qty != default_qty:
                frappe.throw(
                    _("Conversion factor for default Unit of Measure must be {0} in row {1}").format(default_qty, d.idx)
                )

def get_users_with_role(role):
    """
    Get the users with the role

    Args:
        role: Valid role
    """
    enabled_users = frappe.get_all("User",{'enabled':1})
    enabled_users_ = [i.name for i in enabled_users if i.name!="Administrator"]
    required_users = frappe.get_all("Has Role",{'role':role,'parent':['In',enabled_users_]},['parent'])
    if required_users:
        return [i.parent for i in required_users]
    return []


def on_update(doc,ev):
    approvers = False
    # "Send workflow action emails to various employees based on the value of the workflow state field"
    if doc.workflow_state == 'Pending HOD Approval':
        approvers = [doc.department_manager]

    elif doc.workflow_state == 'Pending Procurement Manager Approval':
        #Get all the employees with purchase manager role
        approvers = get_users_with_role("Purchase Manager")

    elif doc.workflow_state == 'Pending Finance Manager':
        approvers = get_users_with_role('Finance Manager')

    elif doc.workflow_state == 'Draft':
        approvers = [doc.owner]

    if approvers and len(approvers) > 0:
        send_workflow_action_email(doc, approvers)
        doc.add_comment("Info", "Email Sent to approvers {0}".format(approvers))
        create_notification_log(_(f"Workflow Action from {frappe.session.user}"), _(f'Please note that a workflow action created by {frappe.session.user} is awaiting your review'), approvers, doc)

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
def get_supplier_list(doctype, txt, searchfield, start, page_len, filters):
    if filters.get('request_for_quotation'):
        query = """
            select
                s.supplier
            from
                `tabRequest for Supplier Quotation` rfq, `tabRequest for Supplier Quotation Supplier` s
            where
                s.parent=rfq.name and rfq.name=%(request_for_quotation)s and s.supplier like %(txt)s
        """
        return frappe.db.sql(query,
            {
                'request_for_quotation': filters.get("request_for_quotation"),
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )
    else:
        return frappe.db.sql("""select name from `tabSupplier` where name like %(txt)s""",
            {
                'start': start,
                'page_len': page_len,
                'txt': "%%%s%%" % txt
            }
        )
def close_assignments(doc):
    "Close Todos for RFP when purchase order is being created"
    if doc.one_fm_request_for_purchase:
        purchase_users = get_users_with_role('Purchase User')
        for each in purchase_users:
            remove_assignment("Request for Purchase", doc.one_fm_request_for_purchase,each)

def set_quotation_attachment_in_po(doc, method):
    if doc.one_fm_request_for_purchase:
        doc.purchase_type = frappe.db.get_value("Request for Purchase",doc.one_fm_request_for_purchase,'type')
        close_assignments(doc)
        quotations = frappe.get_list('Quotation From Supplier', {'request_for_purchase': doc.one_fm_request_for_purchase})
        if len(quotations) > 0:
            set_attachments_to_doctype('Quotation From Supplier', quotations, doc.doctype, doc.name)

def set_attachments_to_doctype(source_dt, list_of_source, target_dt, target_name):
    for source in list_of_source:
        """Copy attachments"""
        from frappe.desk.form.load import get_attachments
        #loop through attachments
        for attach_item in get_attachments(source_dt, source.name):
            #save attachments to new doc
            _file = frappe.get_doc({
            "doctype": "File",
            "file_url": attach_item.file_url,
            "file_name": attach_item.file_name,
            "attached_to_name": target_name,
            "attached_to_doctype": target_dt,
            "folder": "Home/Attachments"})
            _file.save()

def set_po_letter_head(doc, method):
	if doc.workflow_state == "Approved" and not doc.letter_head:
		if frappe.db.exists('Letter Head', {'name': 'Authorization Signature'}):
			doc.db_set('letter_head', 'Authorization Signature')


def validate_store_keeper_project_supervisor(doc, method):
    user = frappe.session.user
    user_emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    roles_check = "Warehouse Supervisor" in frappe.get_roles()
    if doc.set_warehouse:
        warehouse_manager = frappe.db.get_value("Warehouse", doc.set_warehouse, "one_fm_store_keeper")
        if warehouse_manager:
            emp = frappe.db.get_value("Employee", warehouse_manager, "name")
            if not emp == user_emp:
                frappe.throw("You are not authorized to generate the receipt !")
            else:
                return

    if doc.project:
        project_manager = frappe.db.get_value("Project", doc.project, "account_manager")
        if project_manager:
            if not project_manager == user_emp:
                frappe.throw("You are not authorized to generate this receipt !")
            else:
                return

    if not roles_check:
        frappe.throw("You are not authorized to generate this receipt !")
    else:
        return
