# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from one_fm.api.notification import create_notification_log

def todo_after_insert(doc, method):
    doctypes = ['Work Permit', 'Medical Insurance']
    if doc.reference_type in doctypes and doc.reference_name and doc.owner and 'GRD Operator' in frappe.get_roles(doc.owner):
        if not frappe.db.get_value(doc.reference_type, doc.reference_name, 'grd_operator'):
            frappe.db.set_value(doc.reference_type, doc.reference_name, 'grd_operator', doc.owner)

@frappe.whitelist()
def notify(**args):#Notifying operation and transportation department for fingerprint appointment of an employee
	doc = frappe.get_doc('Fingerprint Appointment',args.get("name"))
	email = args.get("email")
	subject = ("Employee of civilid:{civilid}  will have fingerprint appointment at {day_time}.".format(civilid=args.get("civilid"),day_time=args.get("date_time")))
	message = ("Employee of civilid:{civilid}  will have fingerprint appointment at {day_time}.".format(civilid=args.get("civilid"),day_time=args.get("date_time")))
	frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=message,
            )
	create_notification_log(subject, message, [email] ,doc)
	