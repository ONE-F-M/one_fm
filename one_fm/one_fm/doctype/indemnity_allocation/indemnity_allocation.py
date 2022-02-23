# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe import _
import frappe
from frappe.utils import getdate, nowdate
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

def get_per_day_indemnity_allocation(date_of_joining, to_date):
    """To Calculate indemnity of the employee per day distributed across one year. 
    This allows to get the per day calculation to be allocated every day.

    Args:
        date_of_joining ([date]): Employee's Joining Date
        to_date ([data]): up until date

    Returns:
        [type]: [description]
    """
    total_working_year = relativedelta(to_date, date_of_joining).years
    total_working_days = (to_date - date_of_joining).days

    #calculate indemnity per day.
    if total_working_year < 5:
        return 15  / 365
    elif total_working_year >= 5 and total_working_days > (5*365):
        return 30 / 365 

def allocate_daily_indemnity():
    # Get List of Indemnity Allocation for today
    allocation_list = frappe.get_all("Indemnity Allocation", filters={"expired": ["!=", 1]}, fields=["name"])
    for alloc in allocation_list:
        allow_allocation = True
        allocation = frappe.get_doc('Indemnity Allocation', alloc.name)
        date_of_joining = frappe.get_value("Employee",{"name":allocation.employee},["date_of_joining"])
        indemnity_amount = frappe.get_value("Salary Structure Assignment",{"employee":allocation.employee},["indemnity_amount"])

        # Set Daily Allocation
        allocation.new_indemnity_allocated = get_per_day_indemnity_amount(date_of_joining, getdate(nowdate()) , indemnity_amount)
        allocation.total_indemnity_allocated = allocation.total_indemnity_allocated+allocation.new_indemnity_allocated
        allocation.save()