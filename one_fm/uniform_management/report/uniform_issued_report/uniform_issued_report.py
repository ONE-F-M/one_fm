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
        _("Employee") + ":Link/Employee:150",
		_("Employee ID") + ":Data:150",
		_("Employee Name") + ":Data:150",
        _("Item") + ":Data:150",
        _("Issued") + ":Date:150",
        _("Issued Qty") + ":Data:150",
		_("Returned Qty") + ":Data:120"
        ]

def get_data():
	data=[]
	query = """
		select
			u.employee, u.employee_id, u.employee_name, ui.item, ui.issued_on, ui.quantity, ui.returned
		from
			`tabEmployee Uniform` u, `tabEmployee Uniform Item` ui
		where
			u.name = ui.parent and u.type='Issue'
	"""
	uniform_list=frappe.db.sql(query,as_dict=1)
	for uniform in uniform_list:
		row = [uniform.employee, uniform.employee_id, uniform.employee_name, uniform.item, uniform.issued_on, uniform.quantity, uniform.returned]
		data.append(row)

	return data
