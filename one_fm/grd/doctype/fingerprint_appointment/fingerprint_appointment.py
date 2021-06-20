# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url, date_diff
from frappe.model.document import Document
from one_fm.grd.doctype.medical_insurance import medical_insurance
class FingerprintAppointment(Document):

    def validate(self):
        self.set_grd_values()
        self.notify_grd_operator_fp_record()
          
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
         if self.schedule_appointment == "No" or not self.date_and_time_confirmation or self.preparing_documents == "No":
             frappe.throw(_("Upload Required Documents To Submit"))

    def notify_grd_operator_fp_record(self):
        if self.grd_operator:
            page_link = get_url("/desk#Form/Fingerprint Appointment/" + self.name)
            message = "<p>Please Apply for Fingerprint Appointment<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = 'Apply for Fingerprint Appointment Online for'
            send_email(self, [self.grd_operator], message, subject)
            create_notification_log(subject, message, [self.grd_operator], self)

def get_employee_list():
    today = date.today()
    employee_list = frappe.db.get_list('Employee',['employee','residency_expiry_date'])
    for employee in employee_list:
        if date_diff(employee.residency_expiry_date,today) == 45: 
            #print(employee.residency_expiry_date)
           creat_fp_record(frappe.get_doc('Employee',employee.employee))
           
def creat_fp_record(employee):
    if employee.one_fm_nationality == "Nepali" or employee.one_fm_nationality == "Bangladeshi" or employee.one_fm_nationality == "Pakistani":
        fp = frappe.new_doc('Fingerprint Appointment')
        fp.employee = employee.name
        fp.fingerprint_appointment_type = "Renewal Non-Kuwaiti"
        fp.save()

#create a transfer fp record 
def create_fp_record_for_transfer(employee):
    fp = frappe.new_doc('Fingerprint Appointment')
    fp.employee = employee.name
    fp.fingerprint_appointment_type = "Local Transfer"
    fp.date_of_application = today()
    fp.save()

# System Chcek at 4pm (loop) => Notify GRD Operator at 8:30 am next day
def system_check_fp_scheduled_first():#issue
    filter1 = {'schedule_appointment':'No', 'docstatus': 0}
    fp_records1 = frappe.db.get_list('Fingerprint Appointment',filter1,['name', 'grd_operator','grd_supervisor'])
    if len(fp_records1) > 0:
        fp_notify_first_grd_operator()#NEED TO BE DISCUSSED WITH JAMSHEER

# System Chcek at 4pm (loop)
def system_check_fp_scheduled_second():#issue
    filter2 = {'schedule_appointment':'Yes','notify_operations':0, 'docstatus': 0}
    fp_records2 = frappe.db.get_list('Fingerprint Appointment',filter2,['name', 'operations_manager'])
    if len(fp_records2) > 0:
        fp_notify_operations(filter2)

# System Chcek at 4pm (loop)
def system_check_fp_scheduled_third():#issue
    today = date.today()
    filter3 = {'schedule_appointment':'Yes','preparing_documents_notification': today,'preparing_documents':'No','docstatus': 0}
    fp_records3 = frappe.db.get_list('Fingerprint Appointment',filter3,['name', 'grd_operator','grd_supervisor','date_and_time_confirmation'])
    if len(fp_records3) > 0:
        fp_notify_grd_to_prepare_documents_first()

# System Chcek at 4pm (loop)
def system_check_fp_scheduled_Fourth():#issue
    today = date.today()
    filter = {'schedule_appointment':'Yes','date_and_time_confirmation': today,'preparing_documents':'Yes','docstatus': 0}
    fp_records = frappe.db.get_list('Fingerprint Appointment',filter,['name', 'grd_operator','grd_supervisor','date_and_time_confirmation'])
    if len(fp_records) > 0:
        fp_notify_grd_to_submit_first()

def notify_grd_operator_prepare_fp_documents():#(at 2 pm everyday need to be notify)
    """ Notify GRD operator to prepare the fp documents before 1 day of the appointment at 2pm """
    today = date.today()
    filters = {'schedule_appointment':'Yes', 'preparing_documents':'No','docstatus': 0,'preparing_documents_notification': today}
    fp_records = frappe.db.get_list('Fingerprint Appointment',filters,['name', 'grd_operator','grd_supervisor','date_and_time_confirmation'])
    if len(fp_records) > 0:
        page_link = get_url("/desk#Form/Fingerprint Appointment/" + fp_records.name)
        message = "<p>Fingerprint Appointments<a href='{0}'>{1}</a> Applied by {2}.</p>".format(page_link, fp_records.name, fp_records.grd_operator)
        subject = 'Prepare Documents 1.Original Passport 2.Appointment Letter for '
        send_email(fp_records, [fp_records.grd_operator], message, subject)
        create_notification_log(subject, message, [fp_records.grd_operator], fp_records)
           
def notify_grd_operator_to_submit_application():
    """ Notify GRD operator to submit fp """
    today = date.today()
    filters = {'schedule_appointment':'Yes','preparing_documents':'Yes','docstatus': 0,'date_and_time_confirmation': today}
    print(today)
    fp_records = frappe.db.get_list('Fingerprint Appointment',filters,['name', 'grd_operator','grd_supervisor','date_and_time_confirmation'])
    if len(fp_records) > 0:
        page_link = get_url("/desk#Form/Fingerprint Appointment/" + fp_records.name)
        message = "<p>Fingerprint Appointments<a href='{0}'>{1}</a>.</p>".format(page_link, fp_records.name)
        subject = 'Submit the FP for '
        send_email(fp_records, [fp_records.grd_operator], message, subject)
        create_notification_log(subject, message, [fp_records.grd_operator], fp_records)

# Notify GRD Operator at 8:30 am 
def fp_notify_first_grd_operator():
    notify_grd_operator('yellow')

# Notify GRD Operator at 9:00 am 
def fp_notify_again_grd_operator():
    notify_grd_operator('red')

# Notify operations at 4pm 
def fp_notify_operations(filter2):
    notify_operations('yellow',filter2)

# Notify GRD Operator at 2:30 am 
def fp_notify_grd_to_prepare_documents_first():
    notify_grd_operator_documents('yellow')

# Notify GRD Operator at 3:00 am 
def fp_notify_grd_to_prepare_documents_again():
    notify_grd_operator_documents('red')

# Notify GRD Operator at 2:30 pm
def fp_notify_grd_to_submit_first():
    notify_grd_operator_submit('yellow')

# Notify GRD Operator at 3:00 pm 
def fp_notify_grd_to_prepare_documents_again():
    notify_grd_operator_submit('red')

def notify_operations(reminder_indicator,filters):
    """ Notify Operations Dep with the fp appoitment time and date """
    fp_list = frappe.db.get_list('Fingerprint Appointment', filters, ['name', 'operations_manager'])
    if len(fp_list) > 0:
        page_link = get_url("/desk#Form/Fingerprint Appointment/" + fp_list.name)
        message = "<p>Fingerprint Appointments<a href='{0}'>{1}</a> Applied by {2}.</p>".format(page_link, fp_list.name, fp_list.grd_operator)
        subject = 'Apply for Fingerprint Appointment Online for'
        send_email(fp_list, [fp_list.operations_manager], message, subject)
        create_notification_log(subject, message, [fp_list.operations_manager], fp_list)
    frappe.db.set_value("Fingerprint Appointment", filters, 'notify_operations', 1)

def notify_grd_operator(reminder_indicator):
    """ Notify GRD Operator first and second time to remind applying online for fp """
    filters = {'docstatus': 0,'schedule_appointment':['=','No'],'reminded_grd_operator': 0, 'reminded_grd_operator_again':0}
    if reminder_indicator == 'red':
        filters['reminded_grd_operator'] = 1
        filters['reminded_grd_operator_again'] = 0                                                       
    fp_list = frappe.db.get_list('Fingerprint Appointment', filters, ['name','grd_operator','grd_supervisor'])
    cc = [fp_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_operator', fp_list, reminder_indicator, 'Apply', cc)
    
    if reminder_indicator == 'red':
        field = 'reminded_grd_operator_again'
    elif reminder_indicator == 'yellow':
        field = 'reminded_grd_operator'
    frappe.db.set_value("Fingerprint Appointment", filters, field, 1)

def notify_grd_operator_documents(reminder_indicator):
    """ Notify GRD Operator first and second time to remind preparing documents for fp """
    filters = {'docstatus': 0,'schedule_appointment':'Yes','preparing_documents':'No','reminded_grd_operator_documents': 0, 'reminded_grd_operator_documents_again':0}
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

def notify_grd_operator_submit(reminder_indicator):
    """ Notify GRD Operator first and second time to remind submitting fp """                      
    filters = {'docstatus': 0,'schedule_appointment':'Yes','preparing_documents':'Yes','reminded_grd_operator_submit': 0, 'reminded_grd_operator_submit_again':0}
    if reminder_indicator == 'red':
        filters['reminded_grd_operator_submit'] = 1
        filters['reminded_grd_operator_submit_again'] = 0                                                       
    fp_list = frappe.db.get_list('Fingerprint Appointment', filters, ['name', 'grd_operator', 'grd_supervisor'])
    
    cc = [fp_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_operator', fp_list, reminder_indicator, 'Prepare Documents', cc)
    
    if reminder_indicator == 'red':
        field = 'reminded_grd_operator_submit_again'
    elif reminder_indicator == 'yellow':
        field = 'reminded_grd_operator_submit'
    frappe.db.set_value("Fingerprint Appointment", filters, field, 1)


def email_notification_to_grd_user(grd_user, fp_list, reminder_indicator, action, cc=[]):
    recipients = {}

    for fp in fp_list:
        page_link = get_url("/desk#Form/Fingerprint Appointment/"+fp.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, fp.name)
        if fp[grd_user] in recipients:
            recipients[fp[grd_user]].append(message)#add the message in the empty list
        else:
            recipients[fp[grd_user]]=[message]

    if recipients:
        for recipient in recipients:
            subject = 'Fingerprint Appointment {0}'.format(fp.name)#added
            message = "<p>Please {0} Fingerprint Appointment listed below</p><ol>".format(action)
            for msg in recipients[recipient]:
                message += "<li>"+msg+"</li>"
            message += "<ol>"
            frappe.sendmail(
                recipients=[recipient],
                cc=cc,
                subject=_('{0} Fingerprint Appointment'.format(action)),
                message=message,
                header=['Fingerprint Appointment Reminder', reminder_indicator],
            )
            to_do_to_grd_users(_('{0} Fingerprint Appointment'.format(action)), message, recipient)
            create_notification_log(subject, message, [fp.grd_user], fp)#added

def to_do_to_grd_users(subject, description, user):
    frappe.get_doc({
        "doctype": "ToDo",
        "subject": subject,
        "description": description,
        "owner": user,
        "date": today()
    }).insert(ignore_permissions=True)

def send_email(doc, recipients, message, subject):
	frappe.sendmail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)
   