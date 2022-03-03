from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.print_format import download_pdf, print_by_server
from one_fm.processor import sendemail

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
def send_bulk_accommodation_policy_one_by_one(accommodation, recipients = ['j.poil@armor-services.com']):
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
        enqueue(method=sendmail, queue='short', timeout=300, is_async=True, **email_args)

@frappe.whitelist()
def send_bulk_accommodation_policy(accommodation, recipients = ['j.poil@armor-services.com']):
    checkin_list = frappe.db.get_list('Accommodation Checkin Checkout', filters={'accommodation': accommodation, 'type':'IN'}, fields=['name', 'employee_id'])
    attachments = []
    send = False
    i = 1
    for checkin in checkin_list:
        # print_by_server('Accommodation Checkin Checkout', checkin.name, print_format='Accommodation Policy', doc=None, no_letterhead=0)
        print(i)
        print(checkin.name)
        send = False
        attachments.append(frappe.attach_print('Accommodation Checkin Checkout', checkin.name, file_name=checkin.employee_id, print_format='Accommodation Policy'))
        if i == 40:
            send_policy(recipients, accommodation, attachments)
            i = 0
            attachments = []
            send = True
        i += 1

    if not send:
        send_policy(recipients, accommodation, attachments)

def send_policy(recipients, accommodation, attachments):
    from frappe.utils.background_jobs import enqueue
    email_args = {
        "recipients": recipients,
        "message": _("Accommodation Policy and Procedure"),
        "subject": 'Accommodation Ploicy for Accommodation {0}'.format(accommodation),
        "attachments": attachments
    }
    enqueue(method=sendemail, queue='short', timeout=300, is_async=True, **email_args)

def execute_monthly():
    remind_accommodation_meter_reading()

def remind_accommodation_meter_reading():
    meter_list = frappe.db.get_list('Accommodation Meter Reading', fields=['name', 'meter_type', 'meter_reference', 'parent', 'parenttype'])
    recipients = ['j.poil@armor-services.com']
    for meter in meter_list:
        email_args = {
            "recipients": recipients,
            "subject": _("Reminder to Record Accommodation Meter Reading"),
            "message": _("Please record {0} Meter Reading for {1}".format(meter.meter_type, meter.meter_reference)),
            "reference_doctype": meter.parenttype,
            "reference_name": meter.parent
        }
        enqueue(method=sendemail, queue='short', timeout=300, is_async=True, **email_args)
