# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data()
	return columns, data

def get_columns():
    return [
		_("Request for Material") + ":Link/Request for Material:150",
		_("Request for Purchase") + ":Link/Request for Purchase:150",
		_("Department") + ":Data:150",
        _("Type") + ":Data:150",
        _("Requested by") + ":Data:200",
		_("Status") + ":Data:120",
		_("Quotation 1") + ":Link/Quotation From Supplier:120",
		_("Quotation 2") + ":Link/Quotation From Supplier:120",
		_("Quotation 3") + ":Link/Quotation From Supplier:120"
        ]

def get_data():
	data=[]
	rfp_list=frappe.db.sql("""select * from `tabRequest for Purchase` where docstatus=1""",as_dict=1)

	for rfp in rfp_list:
		if not rfp.request_for_material:
			continue
		qtn_list = frappe.db.get_list("Quotation From Supplier", {'request_for_purchase': rfp.name})
		qtn_list_len = len(qtn_list)
		row = [
			rfp.request_for_material,
			rfp.name,
			rfp.department,
			rfp.type,
			rfp.requested_by,
			rfp.status,
			qtn_list[0].name if qtn_list_len > 0 else '',
			qtn_list[1].name if qtn_list_len > 1 else '',
			qtn_list[2].name if qtn_list_len > 2 else ''
		]
		data.append(row)

	return data
