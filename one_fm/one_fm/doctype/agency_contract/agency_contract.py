# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today

class AgencyContract(Document):
	pass


def get_valid_agency_contract(agency, date=today()):
	query = """
		select
			*
		from
			`tabAgency Contract`
		where
			docstatus=1 and (%(date_given) between contact_start_date and contact_start_date) and agency=%(agency)s
	"""
	contract = frappe.db.sql(query.format(),{"date_given": getdate(date), "agency": agency}, as_dict = 1)
	return contract if contract else False
