# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.utils import (
	getdate,
	today
)

@frappe.whitelist()
def get_wage_for_employee_incentive(employee, rewarded_by, on_date=today()):
    wage = 0
    basic_salary = frappe.db.get_value('Employee', employee, 'one_fm_basic_salary')
    if basic_salary:
        wage = basic_salary
        if rewarded_by == 'Number of Daily Wage':
            wage = basic_salary / 30 # Assume 30 days in all month
        else:
            salary_structure_assignment = get_employee_salary_structure_assignment(employee, getdate(on_date))
            if salary_structure_assignment.base:
                wage = salary_structure_assignment.base # Monthly total wage defined in the salary strucure
    return wage

def get_employee_salary_structure_assignment(employee, on_date):
    if not employee or not on_date:
        return None
    return frappe.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "from_date": ("<=", on_date),
            "docstatus": 1,
        },
        "*",
        order_by="from_date desc",
        as_dict=True
    )
