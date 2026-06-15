# one_fm/patches/v15_0/backfill_ojt_employee_schedules.py
import frappe


def execute():
    """Backfill Employee Schedules for OJT-06-2026-0041.

    This OJT was approved before schedule creation moved to on_submit, so no
    Employee Schedules were ever created for it. create_or_update_employee_schedules()
    is idempotent (get_or_create), so this is a no-op if schedules already exist.
    """
    # ojt_name = "OJT-06-2026-0041"
    ojt_name = "OJT-06-2026-0036"

    if not frappe.db.exists("On the Job Training", ojt_name):
        return

    doc = frappe.get_doc("On the Job Training", ojt_name)

    if not doc.employee or not doc.start_date:
        return

    doc.create_or_update_employee_schedules()
    frappe.db.commit()
