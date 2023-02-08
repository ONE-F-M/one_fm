import frappe
from frappe.utils import add_days
import datetime

def before_insert(doc, events):
    """
        Before insert events to execute
    """
    if not frappe.db.exists("Employee", {'name':doc.employee, 'status':'Active'}):
        frappe.throw(f"{doc.employee} - {doc.employee_name} is not active and cannot be assigned to a shift")
    if doc.shift_type:
        shift = frappe.get_doc("Shift Type", doc.shift_type)
        doc.start_datetime = f"{doc.start_date} {(datetime.datetime.min + shift.start_time).time()}"
        if shift.end_time.total_seconds() < shift.start_time.total_seconds():
            doc.end_datetime = f"{add_days(doc.start_date, 1)} {(datetime.datetime.min + shift.end_time).time()}"
        else:
            doc.end_datetime = f"{doc.start_date} {(datetime.datetime.min + shift.end_time).time()}"

def validate(doc, events):
    pass