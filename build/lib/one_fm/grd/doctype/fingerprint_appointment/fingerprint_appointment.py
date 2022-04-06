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
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from one_fm.processor import sendemail


class FingerprintAppointment(Document):

    def validate(self):
        self.set_grd_values()

    def on_update(self):
        self.check_workflow()
        self.check_appointment_date()
        
    def on_submit(self):
        self.db_set('status', 'Completed')
        self.db_set('completed_on', now_datetime())
        # if self.work_permit_type == "Local Transfer":
        #     self.recall_create_medical_insurance_transfer()

    def recall_create_medical_insurance_transfer(self):
        medical_insurance.creat_medical_insurance_for_transfer(self.employee)

    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator_renewal:
            self.grd_operator_renewal = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
        if not self.grd_operator_transfer:
            self.grd_operator_transfer = frappe.db.get_single_value("GRD Settings","default_grd_operator_transfer")
    
    # def validate_mendatory_fields(self):
    #      if not self.date_and_time_confirmation or self.preparing_documents == "No":
    #          frappe.throw(_("Note: You need to prepare Passport and Appointment letter / You Can proceed before one day of the appointment."))
            
    def check_workflow(self):
        if self.workflow_state == "Awaiting for Appointment":
            if self.reminded_grd_operator == 0:
                self.notify_operator_to_apply_for_fp()
                self.reminded_grd_operator = 1

        if self.workflow_state == "Booked":
            field_list = [{'Date and Time Confirmation':'date_and_time_confirmation'},{'Upload Appointment Form':'upload_appointment_form'},{'Required Transportation':'required_transportation'}]
            message_detail = '<b style="color:red; text-align:center;">First, You Need to Apply on <a href="{0}" target="_blank"> Fingerprint Website</a></b>'.format(self.website)
            self.set_mendatory_fields(field_list,message_detail)
            self.notify_site_supervisor()
            self.notify_shift_supervisor()
            if self.required_transportation == "Yes":
                self.notify_transportation()
    
    def before_one_day_of_appointment_date(self):
        today = date.today()
        if date_diff(getdate(self.date_and_time_confirmation),today) == -1 and self.preparing_documents == "No":
            self.notify_operator_to_prepare_for_fp()

    def notify_operator_to_apply_for_fp(self):
        page_link = get_url("/desk#Form/Fingerprint Appointment/" + self.name)
        if self.fingerprint_appointment_type == "Renewal" and self.workflow_state == "Awaiting for Appointment":
            message = "<p>Please Apply for Fingerprint Appointment for Renewal to civil id: <a href='{0}'>{1}</a>.</p>".format(page_link, self.civil_id)
            subject = 'Apply for Fingerprint Appointment for Renewal to civil id:{0} '.format(self.civil_id)
            create_notification_log(subject, message, [self.grd_operator_renewal], self)
            send_email(self, [self.grd_operator_renewal,self.grd_supervisor], message, subject)
        if self.fingerprint_appointment_type == "Local Transfer" and self.workflow_state == "Awaiting for Appointment":
            message = "<p>Please Apply for Fingerprint Appointment for Transfer to civil id: <a href='{0}'>{1}</a>.</p>".format(page_link, self.civil_id)
            subject = 'Apply for Fingerprint Appointment for Renewal to civil id:{0}'.format(self.civil_id)
            create_notification_log(subject, message, [self.grd_operator_transfer], self)
            send_email(self, [self.grd_operator_transfer,self.grd_supervisor], message, subject)

    def notify_operator_to_prepare_for_fp(self):
        page_link = get_url("/desk#Form/Fingerprint Appointment/" + self.name)
        if self.fingerprint_appointment_type == "Renewal" and self.workflow_state == "Booked":
            message = "<p>Please Prepare Fingerprint Appointment Documents for employee with civil id: <a href='{0}'>{1}</a>.</p>".format(page_link, self.civil_id)
            subject = 'Please Prepare Fingerprint Appointment Documents for employee with civil id:{0} '.format(self.civil_id)
            create_notification_log(subject, message, [self.grd_operator_renewal], self)
            send_email(self, [self.grd_operator_renewal,self.grd_supervisor], message, subject)
        if self.fingerprint_appointment_type == "Local Transfer" and self.workflow_state == "Booked":
            message = "<p>Please Prepare Fingerprint Appointment Documents for employee with civil id: <a href='{0}'>{1}</a>.</p>".format(page_link, self.civil_id)
            subject = 'Please Prepare Fingerprint Appointment Documents for employee with civil id:{0}'.format(self.civil_id)
            create_notification_log(subject, message, [self.grd_operator_transfer], self)
            send_email(self, [self.grd_operator_transfer,self.grd_supervisor], message, subject)

    def set_mendatory_fields(self,field_list,message_detail=None):
        mandatory_fields = []
        for fields in field_list:
            for field in fields:
                if not self.get(fields[field]):
                    mandatory_fields.append(field) 
        if len(mandatory_fields) > 0:
            if message_detail:
                message = message_detail
                message += '<br>Mandatory fields required in Fingerprint Appointment form<br><br><ul>'
            else:
                message= 'Mandatory fields required in Fingerprint Appointment form<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' + mandatory_field +'</li>'
            message += '</ul>'
            frappe.throw(message)


    def notify_site_supervisor(self):
        """Notify site supervisor with the employee's appointment"""
        site = frappe.db.get_value("Employee",{'one_fm_civil_id':self.civil_id},['site'])
        if site:
            site_doc = frappe.get_doc("Operations Site",site)
            if site_doc:
                employee = frappe.get_doc("Employee", site_doc.account_supervisor)
                send_email_notification(self, [employee.user_id])
            
    def notify_shift_supervisor(self):
        """Notify shift supervisor with the employee's appointment"""
        shift = frappe.db.get_value("Employee",{'one_fm_civil_id':self.civil_id},['shift'])
        if shift:
            shift_doc = frappe.get_doc("Operations Shift",shift)
            if shift_doc:
                employee = frappe.get_doc("Employee", shift_doc.supervisor)
                send_email_notification(self, [employee.user_id])

    def notify_transportation(self):
        """Notify transportation with the employee's appointment"""
        user_email = "I.ANWARE@one-fm.com"
        content="<h4>Dear "+ user_email +",</h4><p> This email to inform you that Fingerprint Appointment for employee Name: {0} - {1} Required Transportation at {2}.</p>".format(self.full_name,self.employee_id,self.date_and_time_confirmation)  
        sendemail(recipients=[user_email],
            sender=self.grd_supervisor,
            subject="Transportation Required For Fingerprint Appointment", content=content)

    def check_appointment_date(self):
        today = date.today()
        if self.date_and_time_confirmation and getdate(self.date_and_time_confirmation) <= getdate(today):
            frappe.throw(_("You can't set previous/Today's dates"))

def nationality_requires_fp():
    """Getting the nationality that requires Fingerprint"""
    nationalities = frappe.db.get_single_value('Fingerprint Appointment Settings','nationality')
    array = nationalities.split(",")
    return array

# Create fingerprint appointment record once a month for renewals list  
def creat_fp_record(preparation_name):
    nationalities = nationality_requires_fp()
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.nationality in nationalities:
                if employee.renewal_or_extend == "Renewal" or employee.renewal_or_extend == "Local Transfer":
                    creat_fp(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)

#Auto generated everyday at 8am
def get_employee_list():
    today = date.today()
    employee_list = frappe.db.get_list('Employee',['employee','residency_expiry_date'])
    for employee in employee_list:
        if date_diff(employee.residency_expiry_date,today) == -45: 
            creat_fp(frappe.get_doc('Employee',employee.employee))
            
def creat_fp(employee,type,preparation):
    if type == "Renewal":
        fingerprint_appointment_type = "Renewal"
    if type == "Local Transfer":
        fingerprint_appointment_type = "Local Transfer"

    today = date.today()
    fp = frappe.new_doc('Fingerprint Appointment')
    fp.employee = employee.name
    fp.preparation = preparation
    fp.fingerprint_appointment_type = fingerprint_appointment_type
    fp.date_of_application = today
    fp.save(ignore_permissions=True)
           
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

def send_email_notification(doc, recipients):
	page_link = get_url("/desk#Form/Fingerprint Appointment/" + doc.name)
	message = "<p>Please Review the Fingerprint Appointment for employee: {0} at {1}<a href='{2}'>{3}</a>.</p>".format(doc.employee_id,doc.date_and_time_confirmation,page_link, doc.name)
	sendemail(
		recipients= recipients,
		subject='{0} Fingerprint Appointment for employee Name:{1} - {2}'.format(doc.workflow_state, doc.full_name,doc.employee_id),
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)

def send_email(doc, recipients, message, subject):
	sendemail(
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
