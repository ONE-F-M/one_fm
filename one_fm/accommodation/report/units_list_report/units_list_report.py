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
        _("Code/Rerf") + ":Link/Accommodation Unit:100",
		_("Accommodation Code") + ":Data:220",
		_("Total Bed") + ":Data:100",
		_("Occupied Bed") + ":Data:120",
		_("Booked Bed") + ":Data:100",
		_("Temporary Booked") + ":Data:150",
		_("Vacant Bed") + ":Data:100"
    ]

def get_conditions(filters):
    conditions = ""
    if filters.get("accommodation"):
        conditions += " where accommodation='{0}' ".format(filters.get("accommodation"))
    return conditions

def get_data(filters):
	data=[]
	conditions = get_conditions(filters)
	acc_list=frappe.db.sql("""select * from `tabAccommodation Unit` {0}""".format(conditions), as_dict=1)
	for acc in acc_list:
		filters['accommodation_unit'] = acc.name
		filters['disabled'] = 0
		total_no_of_bed_space = frappe.db.count('Bed', filters)
		filters['status'] = 'Occupied'
		occupied_bed = frappe.db.count('Bed', filters)
		filters['status'] = 'Occupied Temporarily'
		occupied_bed += frappe.db.count('Bed', filters)
		filters['status'] = 'Booked'
		booked_bed = frappe.db.count('Bed', filters)
		filters['status'] = 'Vacant'
		vaccant_bed = frappe.db.count('Bed', filters)
		filters['status'] = 'Temporary Booked'
		temporary_booked_bed = frappe.db.count('Bed', filters)
		filters.pop('status')
		row = [
			acc.name,
			acc.accommodation,
			total_no_of_bed_space,
			occupied_bed,
			booked_bed,
			temporary_booked_bed,
			vaccant_bed
		]
		data.append(row)

	return data
