# Copyright (c) 2013, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate

def execute(filters=None):
	columns, data = get_columns(), get_data()
	return columns, data

def get_columns():
    return [
		_("Applicant Name") + ":Data:180",
		_("Date") + ":Data:100",
		_("Contact") + ":Data:180",
		_("Email") + ":Data:180",
		_("Nationality") + ":Link/Nationality:100",
		_("Source") + ":Data:100",
		_("Lead Owner Type") + ":Data:180",
		_("Lead Owner") + ":Link/User:200",
		_("Status") + ":Data:100",
		_("Job Applicant Link") + ":Link/Job Applicant:150",
		_("Job Applicant Status") + ":Data:180",
        ]

def get_data():
	data=[]
	lead_list = frappe.db.sql("""select * from `tabApplicant Lead`""",as_dict=1)
	for lead in lead_list:
		applicant = frappe.db.exists('Job Applicant', {'applicant_lead': lead.name})
		if applicant:
			applicant_status = frappe.db.get_value('Job Applicant', applicant, 'one_fm_applicant_status')
		else:
			applicant = ''
			applicant_status = ''
		row = [lead.applicant_name, formatdate(lead.date), lead.mobile, lead.email_id, lead.nationality, lead.source,
			lead.lead_owner_type, lead.lead_owner, lead.status, applicant, applicant_status]
		data.append(row)
	return data
