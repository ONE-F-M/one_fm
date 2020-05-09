# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
import datetime
# import operator
import re
from datetime import date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        _("Supplier Purchase Order") + ":Link/Supplier Purchase Order:150",
        _("Purchase Request") + ":Link/Purchase Request:150",
        _("Requested By") + ":Link/Employee:150",
        _("Requester Name") + "::200",
        _("Supplier") + ":Link/Supplier:150",
        _("Supplier Name") + "::150",
        _("Place Of Delivery") + ":Link/Warehouse:150",
        _("Delivery Date") + ":Date:150",
        _("Project") + ":Link/Project:150",
        _("Status") + "::100"
        ]


def get_conditions(filters):
    conditions = ""
    doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

    if filters.get("docstatus"):
        conditions += " and docstatus = {0}".format(doc_status[filters.get("docstatus")])

    if filters.get("requested_by"):
        conditions += " and requested_by = '{0}' ".format(filters.get("requested_by"))

    if filters.get("supplier"):
        conditions += " and supplier = '{0}' ".format(filters.get("supplier"))

    if filters.get("project"):
        conditions += " and code = '{0}' ".format(filters.get("project"))

    if filters.get("from_date"):
        conditions += " and delivery_date>='{0}' ".format(filters.get("from_date"))
    if filters.get("to_date"):
        conditions += " and delivery_date<='{0}' ".format(filters.get("to_date"))

    return conditions


def get_data(filters):
    conditions = get_conditions(filters)
    data=[]
    li_list=frappe.db.sql("""select name, purchase_request, requested_by, requester_name, supplier, supplier_name, place_of_delivery, delivery_date, code, docstatus from `tabSupplier Purchase Order` where 1=1 {0} """.format(conditions),as_dict=1)
    
    for purchase in li_list:

        row = [
            purchase.name,
            purchase.purchase_request,
            purchase.requested_by,
            purchase.requester_name,
            purchase.supplier,
            purchase.supplier_name,
            purchase.place_of_delivery,
            purchase.delivery_date,
            purchase.code,
            'Draft' if purchase.docstatus==0 else 'Submitted' if purchase.docstatus==1 else 'Cancelled'
        ]
        data.append(row)

    return data

