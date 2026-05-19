import frappe
def run_test():
    print(getattr(frappe.exceptions.MandatoryError, "http_status_code", 417))
    print(getattr(frappe.exceptions.PermissionError, "http_status_code", 403))
