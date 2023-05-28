# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from hrms.hr.doctype.shift_request.shift_request import ShiftRequest

from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from erpnext.stock.doctype.item_price.item_price import ItemPrice
from erpnext.setup.doctype.employee.employee import Employee
from one_fm.api.doc_methods.shift_request import shift_request_submit, validate_approver, shift_request_cancel, validate_default_shift
from one_fm.api.doc_methods.payroll_entry import (
	validate_employee_attendance, get_count_holidays_of_employee, get_count_employee_attendance, fill_employee_details, create_salary_slips
)
from one_fm.api.doc_methods.salary_slip import (
	get_working_days_details, get_unmarked_days_based_on_doj_or_relieving, get_unmarked_days, get_data_for_eval
)
from one_fm.api.doc_methods.item_price import validate,check_duplicates
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from one_fm.api.mobile.Leave_application import notify_leave_approver
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from one_fm.operations.doctype.contracts.contracts import calculate_item_values

from one_fm.overrides.workflow import filter_allowed_users, get_next_possible_transitions,is_workflow_action_already_created_
from frappe.workflow.doctype.workflow_action import workflow_action


from frappe.desk.doctype.notification_log.notification_log import NotificationLog
from one_fm.api.notification import after_insert
from one_fm.one_fm.payroll_utils import add_tax_components
from one_fm.utils import post_login, validate_reports_to, custom_validate_nestedset_loop
from hrms.overrides.employee_master import EmployeeMaster,validate_onboarding_process
from one_fm.overrides.employee import EmployeeOverride
from frappe.email.doctype.email_queue.email_queue import QueueBuilder,SendMailContext
from one_fm.overrides.email_queue import prepare_email_content as email_content,get_unsubscribe_str_
from frappe.workflow.doctype.workflow_action import workflow_action
from one_fm.utils import override_frappe_send_workflow_action_email

__version__ = '14.3.1'

workflow_action.send_workflow_action_email = override_frappe_send_workflow_action_email

SendMailContext.get_unsubscribe_str = get_unsubscribe_str_
workflow_action.filter_allowed_users = filter_allowed_users
workflow_action.get_next_possible_transitions = get_next_possible_transitions
workflow_action.is_workflow_action_already_created = is_workflow_action_already_created_
SendMailContext.get_unsubscribe_str = get_unsubscribe_str_

QueueBuilder.prepare_email_content  = email_content
EmployeeMaster.validate = EmployeeOverride.validate
EmployeeMaster.validate_onboarding_process = validate_onboarding_process
frappe.auth.LoginManager.post_login = post_login
ShiftRequest.on_submit = shift_request_submit
ShiftRequest.validate_approver = validate_approver
ShiftRequest.on_cancel = shift_request_cancel
ShiftRequest.validate_default_shift = validate_default_shift
PayrollEntry.validate_employee_attendance = validate_employee_attendance
PayrollEntry.get_count_holidays_of_employee = get_count_holidays_of_employee
PayrollEntry.get_count_employee_attendance = get_count_employee_attendance
PayrollEntry.fill_employee_details = fill_employee_details
PayrollEntry.create_salary_slips = create_salary_slips
SalarySlip.get_working_days_details = get_working_days_details
SalarySlip.get_unmarked_days_based_on_doj_or_relieving = get_unmarked_days_based_on_doj_or_relieving
SalarySlip.get_unmarked_days = get_unmarked_days
SalarySlip.add_tax_components = add_tax_components
SalarySlip.get_data_for_eval = get_data_for_eval
ItemPrice.validate = validate
ItemPrice.check_duplicates = check_duplicates
LeaveApplication.notify_leave_approver = notify_leave_approver
calculate_taxes_and_totals.calculate_item_values = calculate_item_values


NotificationLog.after_insert = after_insert
Employee.validate_reports_to = validate_reports_to
frappe.utils.nestedset.validate_loop = custom_validate_nestedset_loop
