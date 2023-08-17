import frappe
from datetime import datetime
from frappe.utils import add_days


def execute():
    """
        Set start and end datetime in schedules
    """
    print("Starting Updating employee schedule datetime.")
    operations_shift = frappe.get_list("Shift Type", fields=["name", "start_time", "end_time"])
    for count, os in operations_shift:
        schedules = frappe.get_list("Employee Schedule", filters={'employee_availability':'Working',
            'shift_type':os.name}, fields=['name', 'date'])
        print(count+1, 'of', len(operations_shift))
        for sc in schedules:
            if sc.date:
                end_date = sc.date
                if os.start_time > os.end_time:
                    end_date = add_days(sc.date, 1)
                start_datetime = f"{sc.date} {os.start_time}"
                end_datetime = f"{end_date} {os.end_time}"
                frappe.db.set_value("Employee Schedule", sc.name, {'start_datetime':start_datetime,
                    'end_datetime':end_datetime}
                )
        frappe.db.commit()
    print("Ending Updating employee schedule datetime.")
