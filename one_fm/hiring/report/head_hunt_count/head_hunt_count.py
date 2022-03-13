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
		_("Source") + ":Data:150",
		_("Creation Date") + ":Date:150",
		_("Total Count") + ":Data:150",
        ]

def get_data():
	data=[]
	head_hunt = frappe.db.get_all("Head Hunt", ["*"])
	for h in head_hunt:
		doc = frappe.get_list("Head Hunt Item",{"parent":h},['count(applicant_name) as count'])
		row = [ h.lead_owner, creation, doc ]
    # for jop in jop_list:
	# 	row = [
	# 		jop.applicant_name,
	# 		jop.job_title,
	# 		jop.one_fm_designation,
	# 		jop.status,
	# 		jop.one_fm_applicant_status,
	# 		jop.one_fm_erf
	# 	]
	# 	data.append(row)
