# one_fm/patches/v15_0/create_attendance_check_jul11_2026.py
import frappe

from one_fm.one_fm.doctype.attendance_check.attendance_check import create_attendance_check


def execute():
    """Create Attendance Check records for 11th July 2026.

    Reuses the standard scheduled entry point, which creates checks for
    absentees and for shift-working employees with no attendance marked on
    the date. The function is guarded by production_domain(), so it only
    does work on the production site.
    """
    create_attendance_check("2026-07-11")
    frappe.db.commit()
