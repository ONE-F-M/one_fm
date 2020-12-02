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
        _("Code/Rer") + ":Link/Request for Purchase:150",
        _("Department") + ":Data:150",
        _("Type") + ":Data:150",
        _("Requested by") + ":Data:200",
		_("Status") + ":Data:120",
		_("Request for Material") + ":Link/Request for Material:150",
        _("Accepted by") + ":Data:150",
		_("Approved by") + ":Data:150",
        ]

def get_data():
	data=[]
	rfm_list=frappe.db.sql("""select * from `tabRequest for Purchase` where docstatus=1""",as_dict=1)

	for rfm in rfm_list:
		accepted = ""
		approved = ""
		row = [
			rfm.name,
			rfm.department,
			rfm.type,
			rfm.requested_by,
			rfm.status,
			rfm.request_for_material,
			accepted,
			approved
		]
		data.append(row)

	return data
