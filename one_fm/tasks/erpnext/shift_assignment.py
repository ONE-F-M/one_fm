import frappe
from frappe.utils import add_days



def before_insert(doc, events):
    """
        Before insert events to execute
    """
    if not frappe.db.exists("Employee", {'name':doc.employee, 'status':'Active'}):
        frappe.throw(f"{doc.employee} - {doc.employee_name} is not active and cannot be assigned to a shift")

    shift = frappe.get_doc("Operations Shift", doc.shift)
    doc.start_datetime = f"{doc.start_date} {shift.start_time}"
    if shift.end_time.total_seconds() < shift.start_time.total_seconds():
        doc.end_datetime = f"{add_days(doc.start_date, 1)} {shift.end_time}"
    else:
        doc.start_datetime = f"{doc.start_date} {shift.end_time}"

