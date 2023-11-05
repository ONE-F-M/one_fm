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
		_("Gender") + ":Data:90",
		_("Rooms") + ":Data:70",
		_("Type A") + ":Data:70",
		_("Type B") + ":Data:70",
		_("Type C") + ":Data:70",
		_("Type D") + ":Data:70",
		_("Type E") + ":Data:70",
		_("Total Bed") + ":Data:100",
		_("Occupied Bed") + ":Data:120",
		_("Vacant Bed") + ":Data:100"
    ]

def get_data(filters):
	data=[]
	acc_list=frappe.db.sql("""select * from `tabAccommodation`""",as_dict=1)
	for acc in acc_list:
		for gender in ["Male", "Female"]:
			filters['accommodation'] = acc.name
			filters['gender'] = gender
			filters['disabled'] = 0
			total_no_of_bed_space = frappe.db.count('Bed', filters)
			totall_no_of_rooms = frappe.db.count('Accommodation Space',
				{'accommodation': acc.name, 'bed_space_available': 1, 'gender': gender})
			type_a = frappe.db.count('Bed', {'accommodation': acc.name, 'gender': gender, 'disabled': 0, 'bed_space_type': 'A'})
			type_b = frappe.db.count('Bed', {'accommodation': acc.name, 'gender': gender, 'disabled': 0, 'bed_space_type': 'B'})
			type_c = frappe.db.count('Bed', {'accommodation': acc.name, 'gender': gender, 'disabled': 0, 'bed_space_type': 'C'})
			type_d = frappe.db.count('Bed', {'accommodation': acc.name, 'gender': gender, 'disabled': 0, 'bed_space_type': 'D'})
			type_e = frappe.db.count('Bed', {'accommodation': acc.name, 'gender': gender, 'disabled': 0, 'bed_space_type': 'E'})
			filters['status'] = 'Occupied'
			occupied_bed = frappe.db.count('Bed', filters)
			filters['status'] = 'Occupied Temporarily'
			occupied_bed += frappe.db.count('Bed', filters)
			filters['status'] = 'Vacant'
			vaccant_bed = frappe.db.count('Bed', filters)
			filters.pop('status')
			row = [
				acc.name,
				acc.accommodation,
				gender,
				totall_no_of_rooms,
				type_a,
				type_b,
				type_c,
				type_d,
				type_e,
				total_no_of_bed_space,
				occupied_bed,
				vaccant_bed
			]
			data.append(row)

	return data
