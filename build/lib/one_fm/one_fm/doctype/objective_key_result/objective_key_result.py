# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import datetime
from datetime import timedelta
from frappe.utils import getdate

# bench execute --args "{'2021-01-01', '2021-03-31'}" one_fm.one_fm.doctype.objective_key_result.objective_key_result.get_objectives

class ObjectiveKeyResult(Document):
	pass



@frappe.whitelist()
def get_objectives(start_date,end_date):
	
	

	query = """
		select *
		from `tabOKR Performance Profile Objective`
		Where  from_date >= %(start_date)s AND to_date<=%(end_date)s

	"""
	return frappe.db.sql(query , {
		"start_date": start_date,
		"end_date": end_date
	} ,as_dict=True)
