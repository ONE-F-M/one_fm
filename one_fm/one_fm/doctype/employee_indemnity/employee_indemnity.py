# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import month_diff, getdate
from frappe.model.document import Document
from one_fm.one_fm.doctype.indemnity_allocation.indemnity_allocation import get_total_indemnity
from dateutil.relativedelta import relativedelta
from datetime import date

class EmployeeIndemnity(Document):
	pass

@frappe.whitelist()
def get_indemnity_for_employee(employee, exit_status, doj, exit_date):
	"""This function calculates the indemnity of an employee with respect to his exit status and exit date.

	Args:
		employee (str): Employee ID
		exit_status (str): "Resignation", "Termination" or "End of Service"
		doj (str): Employee's Date of Joining
		exit_date (str): Employee's date of exit.

	Returns:
		_type_: list of employee's Indemnity Allocation, 
				Indemnity Policy: According to Exit Status), 
				Indemnity Pecent: According to years of experience
				Total Indemnity allowed: Indemnity Allocated untill date of exit.
	"""
	#get employee's Indemnity Allocation
	allocation = frappe.get_doc('Indemnity Allocation', {'employee': employee, 'expired': ['!=', 1]})
	if allocation:
		#get Indemnity Policy for the given exit status
		policy = frappe.get_doc('Indemnity Policy', {'exit_status': exit_status})
		if policy:
			#Employee's experience/working years and Indemnity allocation
			total_working_year = relativedelta(date.today(), getdate(doj)).years
			
			#Indemnity allocation up until exit date
			total_indemnity_allocated = get_total_indemnity(getdate(doj), getdate(exit_date))
			
			indemnity_percentage = 0
			allocation_policy = sorted(policy.indemnity_policy_details, key=lambda x: x.threshold_year)
			#get the percent got the employee's years of experience
			for alloc_policy in allocation_policy:
				if alloc_policy.threshold_year <= total_working_year:
					indemnity_percentage = alloc_policy.indemnity_percentage
			
			#calculate the allocation by applying the percent
			total_indemnity_allowed = total_indemnity_allocated * (indemnity_percentage/100) 
			return {'allocation': allocation.name, 'policy': policy.name,
				'indemnity_percentage': indemnity_percentage, 'total_indemnity_allowed': total_indemnity_allowed}
	return False

@frappe.whitelist()
def get_salary_for_employee(employee):
	#get employee's indemnity Amount from his Salary Structure Assignment
	if employee:
		return frappe.get_value("Salary Structure Assignment",{"employee":employee},["indemnity_amount"])