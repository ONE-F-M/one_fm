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
        _("Purchase Request") + ":Link/Purchase Request:150",
        _("Request for Quotation") + ":Link/Request for Quotation:150",
        _("Requested By") + ":Link/Employee:150",
        _("Requester Name") + "::200",
        _("Purchase Date") + ":Date:150",
        _("Project") + ":Link/Project:150",
        _("Ordered") + "::100",
        _("Status") + "::250"
        ]


def get_conditions(filters):
    conditions = ""
    doc_status = {"Pending": 0, "Submitted": 1, "Rejected": 2}

    if filters.get("docstatus"):
        conditions += " and docstatus = {0}".format(doc_status[filters.get("docstatus")])

    if filters.get("requested_by"):
        conditions += " and requested_by = '{0}' ".format(filters.get("requested_by"))

    if filters.get("project"):
        conditions += " and code = '{0}' ".format(filters.get("project"))

    if filters.get("from_date"):
        conditions += " and purchase_date>='{0}' ".format(filters.get("from_date"))
    if filters.get("to_date"):
        conditions += " and purchase_date<='{0}' ".format(filters.get("to_date"))

    return conditions


def get_data(filters):
    conditions = get_conditions(filters)
    data=[]
    li_list=frappe.db.sql("""select name, request_for_quotation, requested_by, requester_name, purchase_date, code, ordered, docstatus, workflow_state from `tabPurchase Request` where 1=1 {0} """.format(conditions),as_dict=1)
    pending_state = ''

    for purchase in li_list:

        if purchase.workflow_state=='Pending':
            pending_state = 'Waiting for Finance approval'
        elif purchase.workflow_state=='Approved by Financial':
            pending_state = 'Waiting for Managment approval'

        row = [
            purchase.name,
            purchase.request_for_quotation,
            purchase.requested_by,
            purchase.requester_name,
            purchase.purchase_date,
            purchase.code,
            'Yes' if purchase.ordered==1 else 'No',
            pending_state if purchase.docstatus==0 else 'Submitted' if purchase.docstatus==1 else 'Rejected'
        ]
        data.append(row)

    return data
