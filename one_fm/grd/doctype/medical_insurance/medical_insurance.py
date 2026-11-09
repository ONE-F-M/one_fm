# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe.automation.doctype.assignment_rule.assignment_rule
from frappe.model.document import Document
from frappe.utils import today, get_url,getdate, get_year_start
from frappe import _
from datetime import date
from frappe.core.doctype.communication.email import make
from frappe.utils import now_datetime
from one_fm.grd.doctype.residency_payment_request import residency_payment_request
from one_fm.grd.processa import cancel_processes
from one_fm.processor import sendemail
from one_fm.utils import is_scheduler_emails_enabled

class MedicalInsurance(Document):
    def before_insert(self):
        self.cancel_existing()
    
    def cancel_existing(self):
        """Cancel  documents for that employee which were created in previous years"""
        year_threshold = getdate(self.date_of_application).year or getdate().year
        first_day_of_year = getdate(f'01-01-{year_threshold}') #Get the first day of the year
        existing_docs = frappe.get_all(self.doctype,{'date_of_application':['<',first_day_of_year],'name':['!=',self.name],'docstatus':0,'employee':self.employee}, pluck='name')
        if existing_docs:
            for one in existing_docs:
                frappe.db.set_value(self.doctype,one,'workflow_state','Cancelled')
            cancel_processes(self.doctype, existing_docs, _("Replaced by a newer Medical Insurance"))
            frappe.db.commit()

    def validate(self):
        self.set_value()

    def set_value(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")



@frappe.whitelist()
def get_employee_data_from_civil_id(civil_id):
    employee_id = frappe.db.exists('Employee', {'one_fm_civil_id': civil_id})
    if employee_id:
        return frappe.get_doc('Employee', employee_id)

#=======================================================================> Reminder Notification
def system_remind_renewal_operator_to_apply_mi():
    """
    This is a cron method runs every day at 8am. It gets Draft `renewal` Medical Insurance list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")
    medical_insurance_list = frappe.db.get_list('Medical Insurance',
    {'date_of_application':['<=',today()],'workflow_state':APPLY_ONLINE_BY_GR_OPERATOR,'insurance_status':['in',('Renewal','New')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    
    if is_scheduler_emails_enabled():
        notification_reminder(medical_insurance_list,supervisor,renewal_operator,"Renewal or New")


def system_remind_transfer_operator_to_apply_mi():
    """
    This is a cron method runs every day at 8am. It gets Draft `transfer` Medical Insurance list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
    medical_insurance_list = frappe.db.get_list('Medical Insurance',
    {'date_of_application':['<=',today()],'workflow_state':APPLY_ONLINE_BY_GR_OPERATOR,'insurance_status':['=',('Local Transfer')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    
    if is_scheduler_emails_enabled():
        notification_reminder(medical_insurance_list,supervisor,transfer_operator,"Local Transfer")



def notification_reminder(medical_insurance_list,supervisor,operator,type):
    """
    This method sends first, second, reminders and then send third one and cc supervisor in the email
    """
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
    """
    This method send email to the required operator with the list of Medical Insurance that their date of application is today or passed already
    """
    message_list=[]
    for medical_insurance in medical_insurance_list:
        page_link = get_url(frappe.get_doc("Medical Insurance", medical_insurance.name).get_url())
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
        doc.insert(ignore_permissions=True)
