# Copyright (c) 2025, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DepartmentWeeklyReview(Document):
	pass

@frappe.whitelist()
def get_employees_by_department(department):
    return frappe.get_all("Employee",filters={"department": department, "status": "Active"},fields=["name", "employee_name"])

@frappe.whitelist()
def get_blockers_by_department(department):
    department_employees = frappe.get_all("Employee",filters={"department": department, "status": "Active"},fields=["user_id"])
    department_user_ids = [emp["user_id"] for emp in department_employees]

    if not department_user_ids:
        return []

    return frappe.get_all("Blocker",filters={"user": ["in", department_user_ids]},fields=["name", "blocker_details"])

