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
        _("Code/Rer") + ":Link/Request for Material:150",
        _("Department") + ":Data:150",
        _("Type") + ":Data:150",
        _("Requested by") + ":Data:200",
		_("Status") + ":Data:120",
        _("Accepted by") + ":Data:150",
		_("Approved by") + ":Data:150",
        ]

def get_data():
	data=[]
	rfm_list=frappe.db.sql("""select * from `tabRequest for Material` where docstatus=1""",as_dict=1)

	for rfm in rfm_list:
		accepted = rfm.request_for_material_accepter if rfm.status == 'Accepted' else ''
		approved = ""
		if rfm.status == 'Approved':
			approved = rfm.request_for_material_approver
			accepted = rfm.request_for_material_accepter
		row = [
			rfm.name,
			rfm.department,
			rfm.type,
			rfm.requested_by,
			rfm.status,
			accepted,
			approved
		]
		if rfm.status == "Approved" and not rfm.request_for_material_approver:
			continue
		if rfm.status == "Accepted" and not rfm.request_for_material_accepter:
			continue
		data.append(row)

	return data
