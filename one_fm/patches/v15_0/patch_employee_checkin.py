import frappe


def execute():
    """
    This patch set missing shift actual start and end date.
    """
    employee_checkins = frappe.db.get_all(
        "Employee Checkin",
        filters={
            'shift_actual_start': '',
            'date': ['>', '2024-05-20']
        },
        fields = ['name', 'shift_assignment']
    )
    for i in employee_checkins:
        if i.shift_assignment:
            shift = frappe.db.get_value(
                "Shift Assignment",
                i.shift_assignment,
                ['name', 'start_datetime', 'end_datetime'],
                as_dict=1
            )
            frappe.db.sql(f"""
                UPDATE `tabEmployee Checkin`
                SET shift_actual_start='{shift.start_datetime}',
                shift_actual_end='{shift.end_datetime}'
                WHERE name='{i.name}'
            """)