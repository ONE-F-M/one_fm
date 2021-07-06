# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import month_diff, getdate
from frappe.model.document import Document

class EmployeeIndemnity(Document):
	pass

@frappe.whitelist()
def get_indemnity_for_employee(employee, exit_status, doj, exit_date):
	if frappe.db.exists('Indemnity Allocation', {'employee': employee, 'expired': ['!=', 1]}):
		allocation = frappe.get_doc('Indemnity Allocation', {'employee': employee, 'expired': ['!=', 1]})
		policy = frappe.get_doc('Indemnity Policy', {'exit_status': exit_status})
		if policy:
			experiance_in_company = 0
			experiance_in_company_in_months = month_diff(getdate(exit_date), getdate(doj))
			if experiance_in_company_in_months > 0:
				experiance_in_company = experiance_in_company_in_months/12
			indemnity_percentage = 0
			allocation_policy = sorted(policy.indemnity_policy_details, key=lambda x: x.threshold_year)
			for alloc_policy in allocation_policy:
				if alloc_policy.threshold_year <= experiance_in_company:
					indemnity_percentage = alloc_policy.indemnity_percentage
			total_indemnity_allowed = allocation.total_indemnity_allocated * (indemnity_percentage/100)
			return {'allocation': allocation.name, 'policy': policy.name,
				'indemnity_percentage': indemnity_percentage, 'total_indemnity_allowed': total_indemnity_allowed}
	return False
