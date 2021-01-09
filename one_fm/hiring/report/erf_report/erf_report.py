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
		_("ERF") + ":Link/ERF:120",
		_("Initiation") + ":Date:120",
		_("Project") + ":Link/Project:120",
		_("Department") + ":Data:120",
		_("Designation") + ":Data:120",
		_("Type of Recruitment") + ":Data:120",
		_("Requested By") + ":Data:120",
		_("Status") + ":Data:80",
		_("Requirement") + ":Data:100",
		_("Applicants") + ":Data:80",
		_("Selected") + ":Data:80",
        _("Rejected") + ":Data:80",
        _("Joined") + ":Data:80",
		_("No Action") + ":Data:80"
        ]

def get_data():
	data=[]
	erf_list = frappe.db.sql("""select * from `tabERF`""",as_dict=1)
	for erf in erf_list:
		total_no_of_applicants = frappe.db.count('Job Applicant', {'one_fm_erf': erf.erf_code })
		total_no_of_joined = frappe.db.count('Employee', {'one_fm_erf': erf.erf_code })
		total_no_of_rejected = frappe.db.count('Job Applicant', {'one_fm_erf': erf.erf_code, 'status':'Rejected' })
		total_no_of_selected =  frappe.db.count('Job Applicant', {'one_fm_erf': erf.erf_code, 'one_fm_applicant_status':'Selected' })
		total_no_of_no_action = frappe.db.count('Job Offer', {'one_fm_erf': erf.erf_code, 'status':'Awaiting Response' })
		# percentage_count = (total_no_of_joined / erf.number_of_candidates_required)*100
		source_of_hire = frappe.db.get_value('Job Opening', {'one_fm_erf': erf.erf_code}, 'one_fm_source_of_hire');

		row = [
			erf.erf_code,
			erf.erf_initiation,
			erf.project,
			erf.department,
			erf.designation,
			source_of_hire,
			erf.erf_requested_by_name,
			erf.status,
			erf.number_of_candidates_required,
			total_no_of_applicants,
			total_no_of_selected,
			total_no_of_rejected,
			total_no_of_joined,
			total_no_of_no_action
		]
		data.append(row)
	return data
