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
        _("Code/Rerf") + ":Link/Accommodation:100",
        _("Accommodation Name") + ":Data:180",
		_("Total Bed") + ":Data:100",
		_("Occupied Bed") + ":Data:120",
		_("Booked Bed") + ":Data:100",
		_("Temporary Booked") + ":Data:150",
		_("Vacant Bed") + ":Data:100"
    ]

def get_data(filters):
	data=[]
	acc_list=frappe.db.sql("""select * from `tabAccommodation`""",as_dict=1)
	for acc in acc_list:
		filters['accommodation'] = acc.name
		total_no_of_bed_space = frappe.db.count('Bed', filters)
		filters['status'] = 'Occupied'
		occupied_bed = frappe.db.count('Bed', filters)
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
