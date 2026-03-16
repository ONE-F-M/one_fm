# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("company"):
        frappe.throw(_("Company is mandatory"))

    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "label": _("Employee ID"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Available Sick Leave Days"),
            "fieldname": "available_sick_leave_days",
            "fieldtype": "Float",
            "width": 180,
        },
    ]

def get_data(filters):
    company = filters.get("company")
    employees = frappe.get_all(
        "Employee",
        filters={"company": company, "status": "Active"},
        fields=["name", "employee_name"]
    )

    data = []
    leave_type = "Sick Leave"
    today = getdate()

    for emp in employees:
        balance = get_leave_balance_on(emp.name, leave_type, today)
        data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "available_sick_leave_days": balance
        })

    return data
