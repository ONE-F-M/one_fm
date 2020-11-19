# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = get_columns(filters.get('reading_type')), get_data(filters)
	return columns, data

def get_columns(reading_type):
	columns = [_("Accommodation") + ":Link/Accommodation:120"]
	if reading_type == "Unit":
		columns.append(_("Unit") + ":Link/Accommodation Unit:80")
	columns.append(_("Meter Type") + ":Data:100")
	columns.append(_("Meter Ref") + ":Data:100")
	months = ['Jan', 'Feb', 'March', 'April', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
	for month in months:
		columns.append(_(month) + ":Data:80")
	return columns

def get_conditions(filters):
	conditions = ""
	if filters.get('reading_type'):
		conditions += " and reading_type='{0}' ".format(filters.get('reading_type'))
	if filters.get('reading_type')=='Common' and filters.get('accommodation'):
		conditions += " and accommodation={0} ".format(filters.get('accommodation'))
	elif filters.get('reading_type')=='Unit' and filters.get('accommodation_unit'):
		conditions += " and accommodation_unit={0} ".format(filters.get('accommodation_unit'))
	if filters.get('meter_type'):
		conditions += " and meter_type='{0}' ".format(filters.get('meter_type'))
	if filters.get('fiscal_year'):
		start_date, end_date = frappe.db.get_value('Fiscal Year', filters.get('fiscal_year'), ['year_start_date', 'year_end_date'])
		conditions += " and reading_date between '{0}' and '{1}'".format(start_date, end_date)
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
	row_data_list = {}
	reading_list=frappe.db.sql(query.format(conditions), as_dict=1)
	for reading in reading_list:
		if filters.get('reading_type')=='Common':
			if reading.accommodation in row_data_list:
				row_data_list[reading.accommodation].append(reading)
			else:
				row_data_list[reading.accommodation] = [reading]
		elif filters.get('reading_type')=='Unit':
			if reading.accommodation_unit in row_data_list:
				row_data_list[reading.accommodation_unit].append(reading)
			else:
				row_data_list[reading.accommodation_unit] = [reading]

	for key in row_data_list:
		accommodation = ''
		accommodation_unit = ''
		meter_type = ''
		months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
		month_consumption = {}
		for row_data in row_data_list[key]:
			accommodation = row_data.accommodation
			meter_type = row_data.meter_type
			meter_reference = row_data.meter_reference
			if filters.get('reading_type') == "Unit":
				accommodation_unit = row_data.accommodation_unit
			if row_data.month:
				month_consumption[row_data.month] = row_data.consumption
		row_index = 0
		row = [accommodation]
		if filters.get('reading_type') == "Unit":
			row.append(accommodation_unit)
			row_index = 1
		row.append(meter_type)
		row.append(meter_reference)
		for month in months:
			row.append('')
		for month_key in month_consumption:
			row[months.index(month_key)+row_index] = month_consumption[month_key]
		data.append(row)

	return data
