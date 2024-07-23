import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, nowdate, cint , getdate
import datetime
from one_fm.utils import check_existing, get_current_shift


@frappe.whitelist()
def update_onboarding_employee(employee):
    # Set a context flag to indicate an API update (It will affect in 'Employee' validate method)
    frappe.flags.allow_enrollment_update = True

    onboard_employee_exist = frappe.db.exists('Onboard Employee', {'employee': employee.name})
    if onboard_employee_exist:
        onboard_employee = frappe.get_doc('Onboard Employee', onboard_employee_exist.name)
        onboard_employee.enrolled = True
        onboard_employee.enrolled_on = now_datetime()
        onboard_employee.save(ignore_permissions=True)
        frappe.db.commit()

def late_checkin_checker(doc, val_in_shift_type, existing_perm=None):
    if doc.time.time() > datetime.strptime(str(val_in_shift_type["start_time"] + timedelta(minutes=val_in_shift_type["late_entry_grace_period"])), "%H:%M:%S").time():
        if not existing_perm:
            return True