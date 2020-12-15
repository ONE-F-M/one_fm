# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, getdate, month_diff

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
    return [
        _("Employee") + ":Link/Employee:150",
		_("Employee ID") + ":Data:150",
		_("Employee Name") + ":Data:150",
        _("Item") + ":Data:150",
        _("Issued") + ":Date:100",
        _("Issued Qty") + ":Data:100",
		_("Returned Qty") + ":Data:100",
		_("Expire On") + ":Date:100",
		_("Pay Back") + ":Currency:100",
        ]

def get_data(filters):
	data=[]
	conditions = []

	query = """
		select
			u.employee, u.employee_id, u.employee_name, ui.item, ui.issued_on, ui.quantity, ui.returned, ui.rate, ui.expire_on
		from
			`tabEmployee Uniform` u, `tabEmployee Uniform Item` ui
		where
			u.name = ui.parent and u.type='Issue'
	"""

	if filters.employee:
		query += "and u.employee = '%s' "%filters.employee

	uniform_list=frappe.db.sql(query,as_dict=1)
	for uniform in uniform_list:
		pay_back = calculate_amount_pay_back(uniform, filters.returned_on)
		row = [uniform.employee, uniform.employee_id, uniform.employee_name, uniform.item, uniform.issued_on,
			uniform.quantity, uniform.returned, uniform.expire_on, pay_back]
		data.append(row)

	return data

def calculate_amount_pay_back(uniform, returned_on=None):
	pay_back = 0
	if not returned_on:
		returned_on = getdate(today())

	qty_return = uniform.quantity - (uniform.returned or 0)
	if qty_return > 0 and getdate(uniform.expire_on) > getdate(returned_on):
		per_month_rate = (qty_return * uniform.rate) / month_diff(uniform.expire_on, uniform.issued_on)
		pay_back += per_month_rate * month_diff(uniform.expire_on, returned_on)
	return pay_back
