# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
from frappe import _
import frappe
from datetime import date
from frappe.utils import getdate, nowdate
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta

def daily_indemnity_allocation_builder():
    query = """
        select emp.name, emp.date_of_joining
        from `tabEmployee` emp
        left join `tabIndemnity Allocation` ia on emp.name = ia.employee and ia.docstatus = 1 and emp.status = 'Active'
        where ia.employee is NULL
    """
    employee_list = frappe.db.sql(query, as_dict=True)
    print(employee_list)
    indemnity_allocation_builder(employee_list)
    # frappe.enqueue(indemnity_allocation_builder, timeout=600, employee_list=employee_list)

def indemnity_allocation_builder(employee_list):
    for employee in employee_list:
        create_indemnity_allocation(employee)

def create_indemnity_allocation(employee):
    indemnity_amount = frappe.get_value("Salary Structure Assignment",{"employee":employee.name},["indemnity_amount"])

    if indemnity_amount:
        total_indemnity_allocated = get_total_indemnity(employee.date_of_joining,indemnity_amount)
        indemnity_allcn = frappe.new_doc('Indemnity Allocation')
        indemnity_allcn.employee = employee.name
        total_indemnity_allocated = get_total_indemnity(employee.date_of_joining,indemnity_amount)
        indemnity_allcn.from_date = employee.date_of_joining
        indemnity_allcn.new_indemnity_allocated = total_indemnity_allocated
        indemnity_allcn.total_indemnity_allocated = total_indemnity_allocated
        indemnity_allcn.submit()

def get_total_indemnity(date_of_joining, indemnity_amount):
    total_working_year = relativedelta(date.today(), date_of_joining).years
    total_working_days = (date.today() - date_of_joining).days

    if total_working_year < 5:
        total_amount = 15 * indemnity_amount / 365 * total_working_days
    elif total_working_year == 5 and total_working_days > 5*365:
        amount_1 = 15 * indemnity_amount / 365 * total_working_days
        amount_2 = 30 * indemnity_amount / 365 * (total_working_days-5*365)
        total_amount = amount_1+amount_2
    return total_amount


def allocate_daily_indemnity():
    # Get List of Indemnity Allocation for today
    allocation_list = frappe.get_all("Indemnity Allocation", filters={"expired": ["!=", 1]}, fields=["name"])
    for alloc in allocation_list:
        allow_allocation = True
        allocation = frappe.get_doc('Indemnity Allocation', alloc.name)
        # Check if employee absent today then not allow allocation for today
        is_absent = frappe.db.sql("""select name, status from `tabAttendance` where employee = %s and
            attendance_date = %s and docstatus = 1 and status = 'Absent' """,
			(allocation.employee, getdate(nowdate())), as_dict=True)
        if is_absent and len(is_absent) > 0:
            allow_allocation = False

        # Check if employee on leave today and allow allocation for today
        leave_appln = frappe.db.sql("""select name, status, leave_type from `tabLeave Application` where employee = %s and
            (%s between from_date and to_date) and docstatus = 1 and status = 'Rejected'""",
			(allocation.employee, getdate(nowdate())), as_dict=True)
        if leave_appln and len(leave_appln) > 0:
            allow_allocation = False

        if allow_allocation:
            # Set Daily Allocation
            allocation.new_indemnity_allocated = 30/365
            allocation.total_indemnity_allocated = allocation.total_indemnity_allocated+allocation.new_indemnity_allocated
            allocation.save()

def validate_leave_proof_document_requirement(doc, method):
    '''
        Function to validate Is Proof Document Required Flag in Leave Application
        Triger form Validate hook of Leave Application
    '''

    if doc.leave_type and doc.status in ['Open', 'Approved']:
        doc.is_proof_document_required = frappe.db.get_value('Leave Type', doc.leave_type, 'is_proof_document_required')
        if doc.is_proof_document_required and not doc.proof_document:
            frappe.throw(_("Proof Document Required for {0} Leave Type.!".format(doc.leave_type)))