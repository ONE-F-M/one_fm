# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, get_url
from frappe import _
from datetime import date
from frappe.core.doctype.communication.email import make
from frappe.utils import now_datetime
from one_fm.grd.doctype.residency_payment_request import residency_payment_request
from one_fm.grd.doctype.moi_residency_jawazat import moi_residency_jawazat

class MedicalInsurance(Document):
    
    def validate(self):
        self.set_value()
        

    def set_value(self):
        if not self.grd_supervisor: 
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator: 
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    
    def on_submit(self):
        self.set_depend_on_fields()
        self.db_set('medical_insurance_submitted_by', frappe.session.user)
        self.db_set('medical_insurance_submitted_on', now_datetime())
        if self.insurance_status == "Local Transfer":
            self.recall_create_moi_transfer()

    def recall_create_moi_transfer(self):
        moi_residency_jawazat.creat_moi_for_transfer(self.work_permit)

    
    def set_depend_on_fields(self):
        if self.upload_medical_insurance == None:
            frappe.throw(_('Upload Medical Insurance Is Required To Submit'))

#need to be inside the class
def valid_work_permit_exists(preparation_name):
    # TODO: filter work permit records only take the non kuwaiti
    
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal' and employee.nationality != 'Kuwaiti':
                print(employee.employee)
                create_mi_record(frappe.get_doc('Work Permit',{'preparation':preparation_name,'employee':employee.employee}))

#Creating mi for transfer
def creat_medical_insurance_for_transfer(employee_name):
    employee = frappe.get_doc('Employee',employee_name)
    if employee:
        create_mi_record(frappe.get_doc('Work Permit',{'employee':employee.employee}))


def create_mi_record(WorkPermit):
    new_medical_insurance = frappe.new_doc('Medical Insurance')

    if(WorkPermit.work_permit_type == "Renewal Non Kuwaiti"):
        Insurance_status = "Renewal"
        new_medical_insurance.date_of_application = WorkPermit.date_of_application #setting the same date of application of wp
    elif(WorkPermit.work_permit_type == "New Non Kuwaiti"):#Overseas
        Insurance_status = "New" 
    elif (WorkPermit.work_permit_type == "Local Transfer"):#for non kuwaiti <if it is for kuwait called new or renew and they don't have MI process
        Insurance_status = "Local Transfer" # the Insurance_status will be new for overseas only 
        new_medical_insurance.date_of_application = today() #set the date of creation

    new_medical_insurance.work_permit = WorkPermit.name
    new_medical_insurance.preparation = WorkPermit.preparation
    new_medical_insurance.insurance_status = Insurance_status
    new_medical_insurance.passport_expiry_date = WorkPermit.passport_expiry_date
    new_medical_insurance.employee_id = WorkPermit.employee_id
    new_medical_insurance.employee = WorkPermit.employee
    new_medical_insurance.insert()

@frappe.whitelist()
def get_employee_data_from_civil_id(civil_id):
    employee_id = frappe.db.exists('Employee', {'one_fm_civil_id': civil_id})
    if employee_id:
        return frappe.get_doc('Employee', employee_id)
    
############################################################################# Reminder Notification 
def system_remind_renewal_operator_to_apply_mi():# cron job at 8pm
    """This is a cron method runs every day at 8pm. It gets Draft renewal Medical Insurance list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    medical_insurance_list = frappe.db.get_list('Medical Insurance',
    {'date_of_application':['<=',date.today()],'workflow_state':'Apply Online by PRO','insurance_status':['in',('Renewal','New')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    notification_reminder(medical_insurance_list,supervisor,renewal_operator,"Renewal or New")
    

def system_remind_transfer_operator_to_apply_mi():# cron job at 8pm
    """This is a cron method runs every day at 8pm. It gets Draft transfer Medical Insurance list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
    medical_insurance_list = frappe.db.get_list('Medical Insurance',
    {'date_of_application':['<=',date.today()],'workflow_state':'Apply Online by PRO','insurance_status':['=',('Local Transfer')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    notification_reminder(medical_insurance_list,supervisor,transfer_operator,"Local Transfer")
    


def notification_reminder(medical_insurance_list,supervisor,operator,type):
    """This method sends first, second, reminders and then send third one and cc supervisor in the email"""
    first_reminder_list=[] 
    second_reminder_list=[] 
    penality_reminder_list=[] 
    if medical_insurance_list and len(medical_insurance_list) > 0:
        for mi in medical_insurance_list:
            if mi.reminder_grd_operator_again:
                penality_reminder_list.append(mi)
            elif mi.reminder_grd_operator and not mi.reminder_grd_operator_again:
                second_reminder_list.append(mi)
            elif not mi.reminder_grd_operator:
                first_reminder_list.append(mi)

    if penality_reminder_list and len(penality_reminder_list)>0:
        email_notification_reminder(operator,penality_reminder_list,"Third Reminder","Apply for",type,supervisor)
    elif second_reminder_list and len(second_reminder_list)>0:
        email_notification_reminder(operator,second_reminder_list,"Second Reminder","Apply for",type)
        for mi in second_reminder_list:
            frappe.db.set_value('Medical Insurance',mi.name,'reminder_grd_operator_again',1)
    elif first_reminder_list and len(first_reminder_list)>0:
        email_notification_reminder(operator,first_reminder_list,"First Reminder","Apply for",type)
        for mi in first_reminder_list:
            frappe.db.set_value('Medical Insurance',mi.name,'reminder_grd_operator',1)
        
def email_notification_reminder(grd_user,medical_insurance_list,reminder_number, action,type, cc=[]):
    """This method send email to the required operator with the list of Medical Insurance for applying"""
    message_list=[]
    for medical_insurance in medical_insurance_list:
        page_link = get_url("/desk#Form/Medical Insurance/"+medical_insurance.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, medical_insurance.civil_id)
        message_list.append(message)

    if message_list:
        message = "<p>{0}: Please {1} {2} Medical Insurance listed below</p><ol>".format(reminder_number,action,type)
        for msg in message_list:
            message += "<li>"+msg+"</li>"
        message += "<ol>"
        make(
            subject=_('{0}: {1} {2} Medical Insurance'.format(reminder_number,action,type)),
            content=message,
            recipients=[grd_user],
            cc=cc,
            send_email=True,
        )

# Notify GRD Operator to mark mi lists as completed (second time) 
def email_notification_to_grd_user(grd_user, mi_list, reminder_indicator, action, cc=[]):
    recipients = {}
    
    for mi in mi_list:
        page_link = get_url("/desk#Form/Medical Insurance/"+mi.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, mi.name)
        
        if mi[grd_user] in recipients:
            recipients[mi[grd_user]].append(message)
        else:
            recipients[mi[grd_user]]=[message]

    if recipients:
        for recipient in recipients:
            message = "<p>Please {0} Medical Insurance listed below</p><ol>".format(action)
            for msg in recipients[recipient]:
                message += "<li>"+msg+"</li>"
            message += "<ol>"
            frappe.sendmail(
                recipients=[recipient],
                cc=cc,
                subject=_('{0} Medical Insurance'.format(action)),
                message=message,
                header=['Medical Insurance Reminder', reminder_indicator],
            )
            to_do_to_grd_users(_('{0} Medical Insurance'.format(action)), message, recipient)

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

def create_notification_log(subject, message, for_users, reference_doc):
    for user in for_users:
        doc = frappe.new_doc('Notification Log')
        doc.subject = subject
        doc.email_content = message
        doc.for_user = user
        doc.document_type = reference_doc.doctype
        doc.document_name = reference_doc.name
        doc.from_user = reference_doc.modified_by
        doc.insert(ignore_permissions=True)