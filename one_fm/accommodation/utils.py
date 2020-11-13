from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.print_format import download_pdf, print_by_server

@frappe.whitelist()
def accommodation_qr_code_live_details(docname):
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
        format = doctype+' QR Details'
        if not frappe.db.exists('Print Format', {'name': doctype+' QR Details'}):
            format = None
        return download_pdf(doctype, docname, format=format, doc=None, no_letterhead=0)

@frappe.whitelist()
def print_bulk_accommodation_policy(accommodation, recipients = ['j.poil@armor-services.com']):
    from frappe.utils.background_jobs import enqueue
    checkin_list = frappe.db.get_list('Accommodation Checkin Checkout', filters={'accommodation': accommodation, 'type':'IN'}, fields=['name', 'employee_id'])
    i = 0
    for checkin in checkin_list:
        # print_by_server('Accommodation Checkin Checkout', checkin.name, print_format='Accommodation Policy', doc=None, no_letterhead=0)
        print(i)
        print(checkin.name)
        email_args = {
            "recipients": recipients,
            "message": _("Accommodation Policy and Procedure"),
            "subject": 'Accommodation Ploicy for Accommodation {0}'.format(accommodation),
            "attachments": [frappe.attach_print('Accommodation Checkin Checkout', checkin.name, file_name=checkin.employee_id, print_format='Accommodation Policy')],
            "reference_doctype": 'Accommodation Checkin Checkout',
            "reference_name": checkin.name
        }
        enqueue(method=frappe.sendmail, queue='short', timeout=300, is_async=True, **email_args)
