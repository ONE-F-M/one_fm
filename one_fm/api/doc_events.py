import frappe
from frappe.utils import cstr

@frappe.whitelist()
def naming_series(doc, method):
    doc.name = doc.shift_type+"|"+doc.start_time+"-"+doc.end_time+"|"+cstr(doc.duration)+" hours"