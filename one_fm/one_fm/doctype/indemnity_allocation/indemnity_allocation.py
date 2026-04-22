# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe import _
import frappe
from datetime import date
from frappe.utils import getdate, nowdate, flt, create_batch
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta

class IndemnityAllocation(Document):
	pass

def daily_indemnity_allocation_builder():
    """This function creates Indemnity Allocation for the employee
     who do not have an existing indemnity allocation record.
    """

    query = """
        select emp.name, emp.date_of_joining
        from `tabEmployee` emp
        left join `tabIndemnity Allocation` ia on emp.name = ia.employee and ia.docstatus = 1 and emp.status = 'Active'
        where ia.employee is NULL
    """
    employee_list = frappe.db.sql(query, as_dict=True)
    frappe.enqueue(indemnity_allocation_builder, timeout=600, employee_list=employee_list)

def indemnity_allocation_builder(employee_list):
    for employee in employee_list:
        create_indemnity_allocation(employee)

def create_indemnity_allocation(employee):
	"""Create New Indemnity Record based on employee's Joining Date.

	Args:
		employee ([list]): Employee doc
	"""

	to_date = date.today()

	#create indemnity allocation doc 
	indemnity_allcn = frappe.new_doc('Indemnity Allocation')
	indemnity_allcn.employee = employee.name
	total_indemnity_allocated = get_total_indemnity(employee.date_of_joining, to_date )
	indemnity_allcn.from_date = employee.date_of_joining
	indemnity_allcn.new_indemnity_allocated = total_indemnity_allocated
	indemnity_allcn.total_indemnity_allocated = total_indemnity_allocated
	indemnity_allcn.submit()

def get_total_indemnity(date_of_joining, to_date):
    """To Calculate the total Indemnity of an employee based on employee's Joining date.

    Args:
        date_of_joining ([date]): Employee's Joining Date
        to_date ([data]): up until date

    Returns:
        total_allocation: Total Indemnity Allocation calculated from joining date till 'to_date'. 
    """

    #get no. of year and days employee has worked. 
    total_working_year = relativedelta(to_date, date_of_joining ).years
    total_working_days = (to_date - date_of_joining).days

    #reason: Any no. of days after completing 5 years as different calculation. 
    five_year_in_days = 5*365

    # up until 5 years of working year, the monthly calculation takes "15 days" salary in to consideration.
    if total_working_year < 5 or (total_working_year == 5 and total_working_days == 5*365):
        #15 days salary is divided over a year and  that becomes each day's allocation.
        return 15 / 365 * total_working_days
    
    elif total_working_year >= 5 and total_working_days > 5*365:
        #calculation takes 15 days salary for 5 years and 30 days salary after 5 years         
        return (15 / 365 * five_year_in_days) + (30 / 365 * (total_working_days-five_year_in_days))

def get_per_day_indemnity_amount(date_of_joining, to_date, indemnity_amount=0):
	"""To Calculate indemnity of the employee per day distributed across one year.
	This allows to get the per day calculation to be allocated every day.
	Args:
		date_of_joining ([date]): Employee's Joining Date
		to_date ([data]): up until date
		indemnity_amount ([currency]): Indemnity Amount from Salary Structure Assignment
	Returns:
		amount: Per day indemnity amount
	"""
	if not indemnity_amount:
		return 0.0

	total_working_days = (getdate(to_date) - getdate(date_of_joining)).days
	per_day_amount = flt(indemnity_amount) / 26

	# calculate indemnity per day.
	# If total_working_days <= 5 years (1825 days), use 15 days; otherwise use 30 days.
	if total_working_days <= 5 * 365:
		return 15 * per_day_amount / 365
	else:
		return 30 * per_day_amount / 365

def allocate_daily_indemnity():
	# Get List of Indemnity Allocation for today
	allocation_names = frappe.get_all(
		"Indemnity Allocation",
		filters={"expired": ["!=", 1], "docstatus": 1},
		pluck="name"
	)

	for batch in create_batch(allocation_names, 200):
		frappe.enqueue(
			"one_fm.one_fm.doctype.indemnity_allocation.indemnity_allocation.process_allocation_batch",
			allocation_names=batch,
			timeout=600
		)

def process_allocation_batch(allocation_names):
	allocations = frappe.get_all(
		"Indemnity Allocation",
		filters={"name": ["in", allocation_names]},
		fields=["name", "employee", "total_indemnity_allocated"]
	)

	employee_names = [a.employee for a in allocations]

	# Fetch date_of_joining for all employees
	employees = frappe.get_all(
		"Employee",
		filters={"name": ["in", employee_names]},
		fields=["name", "date_of_joining"]
	)
	doj_map = {e.name: e.date_of_joining for e in employees}

	# Fetch latest submitted indemnity_amount from Salary Structure Assignment
	ssa_list = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": ["in", employee_names], "docstatus": 1},
		fields=["employee", "indemnity_amount", "from_date"],
		order_by="from_date desc"
	)

	# Map employee to their latest indemnity_amount
	ssa_map = {}
	for ssa in ssa_list:
		if ssa.employee not in ssa_map:
			ssa_map[ssa.employee] = ssa.indemnity_amount

	today_date = getdate(nowdate())

	for alloc in allocations:
		doj = doj_map.get(alloc.employee)
		indemnity_amount = ssa_map.get(alloc.employee, 0)

		if not doj:
			continue

		new_indemnity = get_per_day_indemnity_amount(doj, today_date, indemnity_amount)
		total_indemnity = flt(alloc.total_indemnity_allocated) + new_indemnity

		frappe.db.set_value(
			"Indemnity Allocation",
			alloc.name,
			{
				"new_indemnity_allocated": new_indemnity,
				"total_indemnity_allocated": total_indemnity
			},
			update_modified=True
		)

	frappe.db.commit()
