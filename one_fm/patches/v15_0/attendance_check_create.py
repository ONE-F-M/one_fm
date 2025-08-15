import frappe
from one_fm.one_fm.doctype.attendance_check.attendance_check import create_attendance_check


def execute():
    frappe.enqueue(create_attendance_check,attendance_date="2025-07-28", queue='long', timeout=7000)