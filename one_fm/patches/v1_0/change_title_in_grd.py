from __future__ import unicode_literals
import frappe
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification,\
	get_title, get_title_html

def execute():
    set_title_wp_as_civil_id()
    set_title_mi_as_civil_id()
    set_title_moi_as_civil_id()
    set_title_fp_as_civil_id()

def set_title_wp_as_civil_id():
    for doc in frappe.get_all('Work Permit'):
        wp_doc = frappe.get_doc('Work Permit',doc.name)
        wp_doc.title = wp_doc.civil_id
        print(doc.name)
        print(wp_doc.title)
        print("===========")

def set_title_mi_as_civil_id():
    for doc in frappe.get_all('Medical Insurance'):
        mi_doc = frappe.get_doc('Medical Insurance',doc.name)
        mi_doc.title = mi_doc.civil_id
        print(doc.name)
        print(mi_doc.title)
        print("===========")

def set_title_moi_as_civil_id():
    for doc in frappe.get_all('MOI Residency Jawazat'):
        moi_doc = frappe.get_doc('MOI Residency Jawazat',doc.name)
        moi_doc.title = moi_doc.one_fm_civil_id
        print(doc.name)
        print(moi_doc.title)
        print("===========")

def set_title_fp_as_civil_id():
    for doc in frappe.get_all('Fingerprint Appointment'):
        fp_doc = frappe.get_doc('Fingerprint Appointment',doc.name)
        fp_doc.title = fp_doc.civil_id
        print(doc.name)
        print(fp_doc.title)
        print("===========")