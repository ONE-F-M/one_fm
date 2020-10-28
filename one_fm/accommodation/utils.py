from __future__ import unicode_literals
import frappe
from frappe.utils.print_format import download_pdf

@frappe.whitelist()
def accommodation_qr_code_live_details(docname, format=None):
    doctype = False
    if frappe.db.exists('Bed', {'name': docname}):
        doctype = 'Bed'
    elif frappe.db.exists('Accommodation Space', {'name': docname}):
        doctype = 'Accommodation Space'
    elif frappe.db.exists('Accommodation Unit', {'name': docname}):
        doctype = 'Accommodation Unit'
    elif frappe.db.exists('Accommodation', {'name': docname}):
        doctype = 'Accommodation'
    if doctype:
        return download_pdf(doctype, docname, format=format, doc=None, no_letterhead=0)
