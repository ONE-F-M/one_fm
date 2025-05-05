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
    department_employees = frappe.get_all("Employee",filters={"department": department, "status": "Active"},fields=["user_id", "employee_name"])
    
    user_id_to_name = {emp["user_id"]: emp["employee_name"] for emp in department_employees}
    department_user_ids = list(user_id_to_name.keys())

    if not department_user_ids:
        return []

    blockers = frappe.get_all("Blocker",filters={"user": ["in", department_user_ids]},fields=["blocker_details", "date", "assigned_to", "user"])

    result = []

    for b in blockers:
        result.append({
            "blocker_details": b["blocker_details"],
            "employee_name": user_id_to_name.get(b["user"], ""),
            "date": b["date"],
            "assigned_to": b["assigned_to"]
        })

    return result


