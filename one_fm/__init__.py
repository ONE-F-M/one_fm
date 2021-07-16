# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from erpnext.hr.doctype.shift_request.shift_request import ShiftRequest
from erpnext.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from erpnext.hr.doctype.salary_slip.salary_slip import SalarySlip
from erpnext.stock.doctype.item_price.item_price import ItemPrice
from one_fm.api.doc_methods.shift_request import shift_request_submit
from one_fm.api.doc_methods.payroll_entry import validate_employee_attendance, get_count_holidays_of_employee, get_count_employee_attendance
from one_fm.api.doc_methods.salary_slip import get_holidays_for_employee,get_leave_details
from one_fm.api.doc_methods.item_price import validate,check_duplicates

__version__ = '0.0.1'


ShiftRequest.on_submit = shift_request_submit
PayrollEntry.validate_employee_attendance = validate_employee_attendance
PayrollEntry.get_count_holidays_of_employee = get_count_holidays_of_employee
PayrollEntry.get_count_employee_attendance = get_count_employee_attendance
SalarySlip.get_holidays_for_employee = get_holidays_for_employee
SalarySlip.get_leave_details = get_leave_details
ItemPrice.validate = validate
ItemPrice.check_duplicates = check_duplicates
