# Copyright (c) 2016, ESS
# License: See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _

def execute(filters=None):
	if not filters: filters = {}

	data_list = get_data(filters)
	columns = get_columns()
	data = []

	if not data_list:
		msgprint(_("No record found"))
		return columns, data

	for d in data_list:
		row = [ d.name, d.applicant_name, d.applicant_rating, d.one_fm_applicant_status, d.one_fm_erf, d.one_fm_agency]
		data.append(row)

	return columns, data


def get_columns():
	columns = [
		_("Job Applicant") + ":Link/Job Applicant:180",
		_("Applicant Name") + ":Data:120",
		_("Average Score") + ":Float:120",
		_("Applicant Status") + ":Data:120",
		_("ERF") + ":Link/ERF:120",
		_("Agency") + ":Link/Agency:120"
	]

	return columns

def get_conditions(filters):
	conditions = ""

	if filters.get("erf"):
		conditions += "and one_fm_erf = %(erf)s"
	if filters.get("agency"):
		conditions += "and one_fm_agency >= %(agency)s"

	return conditions

def get_data(filters):
	conditions = get_conditions(filters)
	query = """
		select
			name, applicant_name, applicant_rating, one_fm_applicant_status, one_fm_erf, one_fm_agency
		from
			`tabJob Applicant`
		where
			docstatus<2 %s order by applicant_name desc"""
	return frappe.db.sql( query % conditions, filters, as_dict=1)
