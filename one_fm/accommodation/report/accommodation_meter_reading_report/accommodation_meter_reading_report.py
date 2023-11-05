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
        _("Accommodation") + ":Link/Accommodation:120",
		_("Unit") + ":Link/Accommodation Unit:80",
		_("Meter Type") + ":Data:120",
		_("Meter Reference") + ":Data:120",
		_("Reading Date") + ":Date:120",
		_("Reading") + ":Float:120",
		_("Consumption") + ":Float:120"
    ]

def get_conditions(filters):
	conditions = ""
	if filters.get('accommodation'):
		conditions += " and reference_doctype='Accommodation' and reference_name={0} ".format(filters.get('accommodation'))
	elif filters.get('accommodation_unit'):
		conditions += " and reference_doctype='Accommodation Unit' and reference_name={0} ".format(filters.get('accommodation_unit'))
	if filters.get('start_date') and filters.get('to_date'):
		conditions += " and reading_date between '{0}' and '{1}'".format(filters.get('start_date'), filters.get('to_date'))
	return conditions

def get_data(filters):
	data=[]
	query = """
		select
			*
		from
			`tabAccommodation Meter Reading Record`
		where
			docstatus = 1 {0}
	"""
	conditions = get_conditions(filters)
	reading_list=frappe.db.sql(query.format(conditions), as_dict=1)
	for reading in reading_list:
		row = [
			reading.accommodation,
			reading.accommodation_unit,
			reading.meter_type,
			reading.meter_reference,
			reading.reading_date,
			reading.current_reading,
			reading.consumption
		]
		data.append(row)

	return data
