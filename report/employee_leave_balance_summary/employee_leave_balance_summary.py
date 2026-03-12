import frappe


def execute(filters=None):
    company = filters.get('company')

    columns = [
        {"fieldname": "employee_id", "label": "Employee ID", "fieldtype": "Data", "width": 120},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "available_sick_leave_days", "label": "Available Sick Leave Days", "fieldtype": "Float", "width": 150}
    ]

    data = []

    employees = frappe.db.sql("""
        SELECT
            name, employee_id, employee_name
        FROM
            `tabEmployee`
        WHERE
            company = %(company)s
    """, {"company": company}, as_dict=True)

    for employee in employees:
        leave_balance = frappe.db.sql("""
            SELECT
                SUM(leave_balance) AS total_sick_leave
            FROM
                `tabLeave Balance`
            WHERE
                employee = %(employee)s AND leave_type = 'Sick Leave'
        """, {"employee": employee.name}, as_dict=True)

        available_sick_leave_days = leave_balance[0].total_sick_leave if leave_balance and leave_balance[0] and leave_balance[0].total_sick_leave else 0

        data.append({
            "employee_id": employee.employee_id,
            "employee_name": employee.employee_name,
            "available_sick_leave_days": available_sick_leave_days
        })

    return columns, data
