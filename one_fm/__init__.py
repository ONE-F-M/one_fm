# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

# HRMS
from hrms.hr.doctype.shift_request.shift_request import ShiftRequest
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation
from hrms.hr.doctype.interview.interview import Interview
from hrms.hr.doctype.interview_feedback.interview_feedback import InterviewFeedback
from hrms.hr.doctype.shift_assignment.shift_assignment import ShiftAssignment
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment
from hrms.hr.doctype.goal.goal import get_children
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from hrms.overrides.employee_master import EmployeeMaster,validate_onboarding_process

# ONFEM overrides
# HRMS
from one_fm.overrides.employee import EmployeeOverride
from one_fm.overrides.interview import validate_interview_overlap
from one_fm.overrides.shift_assignment import ShiftAssignmentOverride
from one_fm.overrides.goal import get_childrens
from one_fm.api.doc_methods.shift_request import shift_request_submit, validate_approver, shift_request_cancel, validate_default_shift
from one_fm.api.mobile.Leave_application import notify_leave_approver
# from one_fm.api.doc_methods.payroll_entry import fill_employee_details
# from one_fm.api.doc_methods.salary_slip import (
# 	get_working_days_details, get_unmarked_days_based_on_doj_or_relieving, get_unmarked_days, get_data_for_eval
# )


# ERPNext
from erpnext.stock.doctype.item_price.item_price import ItemPrice
from erpnext.setup.doctype.employee.employee import Employee
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from erpnext.stock import stock_ledger
from erpnext.controllers.stock_controller import StockController
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

# ONFEM overrides
# ERPNext
from one_fm.operations.doctype.contracts.contracts import calculate_item_values
from one_fm.one_fm.payroll_utils import add_tax_components
from one_fm.overrides.payment_entry import add_party_gl_entries_,get_valid_reference_doctypes_
from one_fm.overrides.stock_ledger import get_valuation_rate_
from one_fm.overrides.stock_controller import make_batches_with_supplier_batch_id
from one_fm.api.doc_methods.item_price import validate,check_duplicates


# Frappe
from frappe.workflow.doctype.workflow_action import workflow_action
from frappe.desk.doctype.notification_log.notification_log import NotificationLog
from frappe.email.doctype.email_queue.email_queue import QueueBuilder,SendMailContext
from frappe.workflow.doctype.workflow_action import workflow_action
from frappe.automation.doctype.assignment_rule.assignment_rule import AssignmentRule
from frappe.core.doctype.user_permission import user_permission

# ONFEM overrides
# Frappe
from one_fm.overrides.workflow import filter_allowed_users, get_next_possible_transitions,is_workflow_action_already_created_
from one_fm.api.notification import after_insert
from one_fm.utils import post_login, validate_reports_to, custom_validate_nestedset_loop, get_existing_leave_count, custom_validate_interviewer
from one_fm.overrides.email_queue import prepare_email_content as email_content,get_unsubscribe_str_
from one_fm.utils import override_frappe_send_workflow_action_email
from one_fm.overrides.assignment_rule import do_assignment
from one_fm.permissions import get_custom_user_permissions


__version__ = '15.0.6'

# Frappe
SendMailContext.get_unsubscribe_str = get_unsubscribe_str_
QueueBuilder.prepare_email_content  = email_content
NotificationLog.after_insert = after_insert
AssignmentRule.do_assignment = do_assignment
user_permission.get_user_permissions = get_custom_user_permissions
workflow_action.send_workflow_action_email = override_frappe_send_workflow_action_email
workflow_action.filter_allowed_users = filter_allowed_users
workflow_action.get_next_possible_transitions = get_next_possible_transitions
workflow_action.is_workflow_action_already_created = is_workflow_action_already_created_
frappe.auth.LoginManager.post_login = post_login
frappe.utils.nestedset.validate_loop = custom_validate_nestedset_loop

# HRMS
ShiftRequest.on_submit = shift_request_submit
ShiftRequest.validate_approver = validate_approver
ShiftRequest.on_cancel = shift_request_cancel
ShiftRequest.validate_default_shift = validate_default_shift
Interview.validate_overlap = validate_interview_overlap
EmployeeMaster.validate = EmployeeOverride.validate
EmployeeMaster.validate_onboarding_process = validate_onboarding_process
LeaveAllocation.get_existing_leave_count = get_existing_leave_count
LeaveApplication.notify_leave_approver = notify_leave_approver
InterviewFeedback.validate_interviewer = custom_validate_interviewer
ShiftAssignment = ShiftAssignmentOverride
SalarySlip.add_tax_components = add_tax_components
# PayrollEntry.fill_employee_details = fill_employee_details to be fixed
# SalarySlip.get_working_days_details = get_working_days_details to be fixed
# SalarySlip.get_unmarked_days_based_on_doj_or_relieving = get_unmarked_days_based_on_doj_or_relieving to be fixed
# SalarySlip.get_unmarked_days = get_unmarked_days to be fixed
# SalarySlip.get_data_for_eval = get_data_for_eval to be fixed

# ERPNext
StockController.make_batches = make_batches_with_supplier_batch_id
PaymentEntry.add_party_gl_entries = add_party_gl_entries_
PaymentEntry.get_valid_reference_doctypes = get_valid_reference_doctypes_
stock_ledger.get_valuation_rate = get_valuation_rate_
ItemPrice.validate = validate
ItemPrice.check_duplicates = check_duplicates
calculate_taxes_and_totals.calculate_item_values = calculate_item_values



