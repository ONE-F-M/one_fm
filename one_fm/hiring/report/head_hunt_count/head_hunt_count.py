# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
    return [
		_("Source") + ":Data:150",
		_("Creation Date") + ":Date:150",
		_("Total Count") + ":Data:150",
        ]

def get_conditions(filters):
	conditions = ""
	if filters.get("source"):
		conditions += " and lead_owner = '{0}' ".format(filters.get("source"))
	if filters.get("from_date"):
		conditions += " and creation>='{0}' ".format(filters.get("from_date"))
	if filters.get("to_date"):
		conditions += " and creation<='{0}' ".format(filters.get("to_date"))
	return conditions

def get_data(filters):
	data=[]
	conditions = get_conditions(filters)

	head_hunt = frappe.db.sql("""SELECT * from `tabHead Hunt` where 1=1 {0} """.format(conditions),as_dict=1)
	for h in head_hunt:
		doc = frappe.db.sql("""SELECT count(*) as count from `tabHead Hunt Item` WHERE parenttype="Head Hunt" AND parent=%s""",(h.name), as_dict=1)
		row = [ h.lead_owner, h.creation, doc[0].count ]
		data.append(row)
	return data