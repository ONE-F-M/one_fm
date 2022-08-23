# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe

from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)


def get_data(filters):
	print(filters)
	conditions = ""
	if filters.date:
		conditions += f" AND creation BETWEEN '{filters.date} 00:00:00.000000' AND '{filters.date} 23:59:59.999999'"
	query = f"""
		SELECT name, ref_report_doctype, creation
		FROM `tabPrepared Report`
		WHERE ref_report_doctype='Roster Projection View'
		{conditions}
	"""
	data = frappe.db.sql(query, as_dict=1)
	for row in data:
		row.name = "<a href='/app/query-report/Roster Projection View/prepared_report_name={row.name}'>{row.name}</a>".format(
			row=row
		)
	return data

def get_columns():
	return [
		{
			'fieldname': 'name',
			'label': _('Data'),
			'fieldtype': 'HTML',
			'width': 120
		},
		{
			'fieldname': 'creation',
			'label': _('Date'),
			'fieldtype': 'Date',
			'width': 200
		}
	]