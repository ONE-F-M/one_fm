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
        _("Code/Rer") + ":Link/Accommodation:150",
        _("Accommodation Name") + ":Data:150",
        _("Type") + ":Link/Accommodation Type:150",
        _("Ownership") + "::200",
        _("PACI") + "::150"
        ]

def get_data():
    data=[]
    acc_list=frappe.db.sql("""select * from `tabAccommodation`""",as_dict=1)

    for acc in acc_list:
        row = [
            acc.name,
            acc.accommodation,
			acc.type,
			acc.ownership,
			acc.accommodation_paci_number
        ]
        data.append(row)

    return data
