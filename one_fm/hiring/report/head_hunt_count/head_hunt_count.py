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
		_("Source") + ":Data:150",
		_("Creation Date") + ":Date:150",
		_("Total Count") + ":Data:150",
        ]

def get_data():
	data=[]
    
	head_hunt = frappe.db.get_all("Head Hunt", ["*"])
	for h in head_hunt:
		doc = frappe.db.sql("""SELECT count(*) as count from `tabHead Hunt Item` WHERE parenttype="Head Hunt" AND parent=%s""",(h.name), as_dict=1)
		row = [ h.lead_owner, h.creation, doc[0].count ]
		data.append(row)
	return data