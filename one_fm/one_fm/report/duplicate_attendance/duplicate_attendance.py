# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        _("Employee ID") + ":Link/Employee:200",
        _("Employee Name") + "::350",
        _("Number Of Attendance Records") + "::250"
        ]

def get_data(filters):
    attendance_date = filters.get("attendance_date")
    roster_type = filters.get("roster_type")
    status = filters.get("status")

    base_query = """
        SELECT name, employee, employee_name, attendance_date, roster_type, COUNT(name) as records 
        FROM `tabAttendance`
        WHERE attendance_date=%s AND roster_type=%s
    """

    params = [attendance_date, roster_type]
    
    # Attach status with base query if set in filter
    if status:
        base_query += " AND status=%s"
        params.append(status)
    
    base_query += """
        GROUP BY employee, attendance_date, roster_type
        HAVING records > 1
    """
    
    result = frappe.db.sql(base_query, params, as_dict=1)

    data = []

    for item in result:
        data.append([
            item.employee,
            item.employee_name,
            item.records
        ])

    return data


