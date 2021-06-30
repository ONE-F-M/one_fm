# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url, date_diff, getdate
from frappe.model.document import Document
from one_fm.grd.doctype.medical_insurance import medical_insurance

class FingerprintAppointment(Document):

    def validate(self):
        self.set_grd_values()
        self.notify_grd_operator_fp_record()

    def on_update(self):
        self.check_appointment_date()
        

    def on_submit(self):
        self.validate_mendatory_fields()
        self.db_set('status', 'Completed')
        self.db_set('completed_on', today())
        if self.work_permit_type == "Local Transfer":
            self.recall_create_medical_insurance_transfer()

    def recall_create_medical_insurance_transfer(self):
        medical_insurance.creat_medical_insurance_for_transfer(self.employee)

    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
        
    def validate_mendatory_fields(self):
         if not self.date_and_time_confirmation or self.preparing_documents == "No":
             frappe.throw(_("Note: You need to prepare Passport and Appointment letter / You Can proceed before one day of the appointment."))

    def notify_grd_operator_fp_record(self):
        if self.workflow_state == "Open":
            page_link = get_url("/desk#Form/Fingerprint Appointment/" + self.name)
            message = "<p>Please Apply for Fingerprint Appointment<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = 'Apply for Fingerprint Appointment Online for {0}'.format(self.first_name_english)
            send_email(self, [self.grd_operator], message, subject)
            create_notification_log(subject, message, [self.grd_operator], self)

    def check_appointment_date(self):
        today = date.today()
        if self.date_and_time_confirmation and getdate(self.date_and_time_confirmation) <= getdate(today):
            frappe.throw(_("You can't set previous dates"))

#Auto generated everyday at 8am
def get_employee_list():
    today = date.today()
    employee_list = frappe.db.get_list('Employee',['employee','residency_expiry_date'])
    for employee in employee_list:
        if date_diff(employee.residency_expiry_date,today) == -45: 
            creat_fp_record(frappe.get_doc('Employee',employee.employee))
            
def creat_fp_record(employee):
    if employee.one_fm_nationality == "Nepali" or employee.one_fm_nationality == "Bangladeshi" or employee.one_fm_nationality == "Pakistani" or employee.one_fm_nationality == "Afghanistan" or employee.one_fm_nationality == "African":
        print(employee.one_fm_nationality)
        fp = frappe.new_doc('Fingerprint Appointment')
        fp.employee = employee.name
        fp.fingerprint_appointment_type = "Renewal Non-Kuwaiti"
        fp.date_of_application = date.today()
        fp.save(ignore_permissions=True)
    
#create a transfer fp record 
def create_fp_record_for_transfer(employee):
    fp = frappe.new_doc('Fingerprint Appointment')
    fp.employee = employee.name
    fp.fingerprint_appointment_type = "Local Transfer"
    fp.date_of_application = today()
    fp.insert()
    fp.save()
       
# Notify GRD Operator at 8:00 am 
def fp_notify_first_grd_operator():
    notify_grd_operator('yellow')

# Notify GRD Operator at 8:30 am 
def fp_notify_again_grd_operator():
    notify_grd_operator('red')

def notify_grd_operator_documents(reminder_indicator):
    """ Notify GRD Operator first and second time to remind preparing documents for fp """
    filters = {'docstatus': 0,'workflow_state':'Booked','preparing_documents':'No','date_and_time_confirmation':['=',today()],'reminded_grd_operator_documents': 0, 'reminded_grd_operator_documents_again':0}
    if reminder_indicator == 'red':
        filters['reminded_grd_operator_documents'] = 1
        filters['reminded_grd_operator_documents_again'] = 0                                                       
    fp_list = frappe.db.get_list('Fingerprint Appointment', filters, ['name', 'grd_operator', 'grd_supervisor'])
    
    cc = [fp_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_operator', fp_list, reminder_indicator, 'Prepare Documents', cc)
    
    if reminder_indicator == 'red':
        field = 'reminded_grd_operator_documents_again'
    elif reminder_indicator == 'yellow':
        field = 'reminded_grd_operator_documents'
    frappe.db.set_value("Fingerprint Appointment", filters, field, 1)


def to_do_to_grd_users(subject, description, user):
    frappe.get_doc({
        "doctype": "ToDo",
        "subject": subject,
        "description": description,
        "owner": user,
        "date": today(),
        "role":"GRD Operator",
        "reference_type":"Fingerprint Appointment"
    }).insert(ignore_permissions=True)

def send_email(doc, recipients, message, subject):
	frappe.sendmail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def create_notification_log(subject, message, for_users, reference_doc):
    for user in for_users:
        doc = frappe.new_doc('Notification Log')
        doc.subject = subject
        doc.email_content = message
        doc.for_user = user
        doc.document_type = reference_doc.doctype
        doc.document_name = reference_doc.name
        doc.from_user = reference_doc.modified_by
