# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from hrms.hr.doctype.shift_request.shift_request import ShiftRequest
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from erpnext.stock.doctype.item_price.item_price import ItemPrice
from one_fm.api.doc_methods.shift_request import shift_request_submit, validate_approver, shift_request_cancel, validate_default_shift
from one_fm.api.doc_methods.payroll_entry import (
	validate_employee_attendance, get_count_holidays_of_employee, get_count_employee_attendance, fill_employee_details
)
from one_fm.api.doc_methods.salary_slip import (
	get_working_days_details, get_unmarked_days_based_on_doj_or_relieving, get_unmarked_days
)
from one_fm.api.doc_methods.item_price import validate,check_duplicates
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from one_fm.api.mobile.Leave_application import notify_leave_approver
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from one_fm.operations.doctype.contracts.contracts import calculate_item_values
from wiki.wiki.doctype.wiki_page.wiki_page import WikiPage
from one_fm.overrides.wiki_page import get_context
from frappe.desk.doctype.notification_log.notification_log import NotificationLog
from one_fm.api.notification import after_insert
from one_fm.one_fm.payroll_utils import add_tax_components

__version__ = '14.0.0'


ShiftRequest.on_submit = shift_request_submit
ShiftRequest.validate_approver = validate_approver
ShiftRequest.on_cancel = shift_request_cancel
ShiftRequest.validate_default_shift = validate_default_shift
PayrollEntry.validate_employee_attendance = validate_employee_attendance
PayrollEntry.get_count_holidays_of_employee = get_count_holidays_of_employee
PayrollEntry.get_count_employee_attendance = get_count_employee_attendance
PayrollEntry.fill_employee_details = fill_employee_details
SalarySlip.get_working_days_details = get_working_days_details
SalarySlip.get_unmarked_days_based_on_doj_or_relieving = get_unmarked_days_based_on_doj_or_relieving
SalarySlip.get_unmarked_days = get_unmarked_days
SalarySlip.add_tax_components = add_tax_components
ItemPrice.validate = validate
ItemPrice.check_duplicates = check_duplicates
LeaveApplication.notify_leave_approver = notify_leave_approver
calculate_taxes_and_totals.calculate_item_values = calculate_item_values
WikiPage.get_context = get_context
NotificationLog.after_insert = after_insert
