import frappe
from frappe.utils import get_datetime

@frappe.whitelist()
def scan_checkpoint(qr_code, latitude, longitude):
    user = frappe.session.user
    employee_id = frappe.get_value("Employee", {"user_id": user}) #Will be None if logged in as Administrator  
    location = latitude + " " + longitude

    print(qr_code, user, employee_id, location, get_datetime())