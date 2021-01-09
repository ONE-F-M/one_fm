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
		_("Applicant Name") + ":Link/Job Applicant:150",
		_("Job Oppening") + ":Link/ob Oppening:150",
		_("Designation") + ":Link/Designation:150",
		_("Final Status") + ":Data:150",
		_("Applicant Status") + ":Data:150",
		_("ERF") + ":Link/ERF:150"
        ]

def get_data():
	data=[]
	jop_list = frappe.db.sql("""select * from `tabJob Applicant`""",as_dict=1)
	for jop in jop_list:
		row = [
			jop.applicant_name,
			jop.job_title,
			jop.one_fm_designation,
			jop.status,
			jop.one_fm_applicant_status,
			jop.one_fm_erf
		]
		data.append(row)
	return data
