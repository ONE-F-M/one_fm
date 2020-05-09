# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, getdate

class DemandLetter(Document):
	pass

def get_valid_demand_letter(agency, date=today()):
	query = """
		select
			*
		from
			`tabDemand Letter`
		where
			docstatus=1 and (%(date_given) between date_of_issue and valid_till_date) and agency=%(agency)s
	"""
	demand_letter = frappe.db.sql(query.format(),{"date_given": getdate(date), "agency": agency}, as_dict = 1)
	return demand_letter if demand_letter else False
