# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.utils.user import get_user_fullname
from one_fm.api.notification import create_notification_log
from frappe.utils.user import get_users_with_role
from frappe.utils import (
    getdate,
    today,
    get_url
)

@frappe.whitelist()
def get_wage_for_employee_incentive(employee, rewarded_by, on_date=today()):
    '''
        this function returns the wage of an employee based on the rewarded_by value
        if rewarded_by == "Number of Daily Wage" returns basic_salary/30
        if rewarded_by == "Percentage of Monthly Wage" returns base(total salary with all allowances) noted in the salary structure assignment

        args:
            employee: employee ID (Example: HR-EMP-00001)
            rewarded_by: "Percentage of Monthly Wage" or "Number of Daily Wage"
            on_date: Payroll Date
    '''
    wage = 0
    basic_salary = frappe.db.get_value('Employee', employee, 'one_fm_basic_salary')
    if basic_salary:
        wage = basic_salary
        if rewarded_by == 'Number of Daily Wage':
            wage = basic_salary / 30 # Assume 30 days in all month
        else:
            salary_structure_assignment = get_employee_salary_structure_assignment(employee, getdate(on_date))
            if salary_structure_assignment.base:
                wage = salary_structure_assignment.base # Monthly total wage defined in the salary structure
    return wage

def get_employee_salary_structure_assignment(employee, on_date):
    '''
        function is used to get Salary Structure Assignment for an employee on a date
    '''
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

def on_update_after_submit_employee_incentive(doc, method):
    send_employee_incentive_workflow_notification(doc)

def on_update_employee_incentive(doc, method):
    send_employee_incentive_workflow_notification(doc)

def send_employee_incentive_workflow_notification(doc):
    '''
        This function is used to send notification to the ERPNext users
        args:
            doc: Object of Employee Incentive
    '''
    if doc.workflow_state == 'Draft':
        notify_employee_incentive_line_manager(doc)

    if doc.workflow_state in ['Approved by Manager', 'Rejected by Manager']:
        notify_employee_incentive_supervisor(doc)

    if doc.workflow_state == 'Approved by Manager':
        # Notify HR for Approval
        notify_user_list = get_user_list_by_role('HR Manager')
        notify_employee_incentive(doc, frappe.session.user, notify_user_list)

    if doc.workflow_state in ['Approved by HR Manager', 'Rejected by HR Manager']:
        notify_employee_incentive_supervisor(doc)
        notify_employee_incentive_line_manager(doc)

    if doc.workflow_state == 'Approved by HR Manager':
        # Notify Finance Team
        notify_user_list = get_user_list_by_role('Employee Incentive Finance Notifier')
        notify_employee_incentive(doc, frappe.session.user, notify_user_list)

def get_user_list_by_role(role):
    users = get_users_with_role(role)
    user_list = []
    for user in users:
        user_list.append(user)
    return user_list

def notify_employee_incentive_supervisor(employee_incentive):
    # Notify Supervisor
    if employee_incentive.owner != "Administrator":
        notify_employee_incentive(employee_incentive, employee_incentive.owner, [employee_incentive.owner])

def notify_employee_incentive_line_manager(employee_incentive):
    # Notify Line Manager
    reports_to = frappe.db.get_value("Employee",{'name':employee_incentive.employee},['reports_to'])
    reports_to_user = frappe.get_value("Employee", {"name": reports_to}, "user_id")
    notify_employee_incentive(employee_incentive, employee_incentive.owner, [reports_to_user])

def notify_employee_incentive(employee_incentive, action_user, notify_user_list):
    '''
        This method is used to notify Employee Incentive workflow_state changes
    '''
    action_user_fullname = get_user_fullname(action_user)
    status = employee_incentive.workflow_state
    if employee_incentive.workflow_state == 'Draft':
        status = 'Drafted'
    url = get_url("/desk#Form/Employee Incentive/" + employee_incentive.name)
    subject = _("Employee Incentive for the Employee {0}.".format(employee_incentive.employee_name))
    message = _("{0} {1} <p>Employee Incentive {2}<a href='{3}'></a></p> for the Employee {4}.".format(action_user_fullname, status, employee_incentive.name, url, employee_incentive.employee_name))
    create_notification_log(subject, message, notify_user_list, employee_incentive)
