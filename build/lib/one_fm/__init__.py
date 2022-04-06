# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from erpnext.hr.doctype.shift_request.shift_request import ShiftRequest
from erpnext.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip
from erpnext.stock.doctype.item_price.item_price import ItemPrice
from erpnext.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment
from one_fm.api.doc_methods.shift_request import shift_request_submit
from one_fm.api.doc_methods.payroll_entry import validate_employee_attendance, get_count_holidays_of_employee, get_count_employee_attendance, fill_employee_details
from one_fm.api.doc_methods.salary_slip import get_holidays_for_employee,get_leave_details
from one_fm.api.doc_methods.item_price import validate,check_duplicates
from erpnext.hr.doctype.leave_application.leave_application import LeaveApplication
from one_fm.api.mobile.Leave_application import notify_leave_approver
from one_fm.hiring.utils import grant_leave_alloc_for_employee
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from one_fm.operations.doctype.contracts.contracts import calculate_item_values


__version__ = '0.12.2'


ShiftRequest.on_submit = shift_request_submit
PayrollEntry.validate_employee_attendance = validate_employee_attendance
PayrollEntry.get_count_holidays_of_employee = get_count_holidays_of_employee
PayrollEntry.get_count_employee_attendance = get_count_employee_attendance
PayrollEntry.fill_employee_details = fill_employee_details
SalarySlip.get_holidays_for_employee = get_holidays_for_employee
SalarySlip.get_leave_details = get_leave_details
ItemPrice.validate = validate
ItemPrice.check_duplicates = check_duplicates
LeaveApplication.notify_leave_approver = notify_leave_approver
LeavePolicyAssignment.grant_leave_alloc_for_employee = grant_leave_alloc_for_employee
calculate_taxes_and_totals.calculate_item_values = calculate_item_values
