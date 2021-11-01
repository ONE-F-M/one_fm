# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe.utils import today, add_days, get_url, date_diff
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from frappe.core.doctype.communication.email import make

class PACI(Document):
    def validate(self):
        self.set_grd_values()

    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_value('GRD Settings', None, 'default_grd_supervisor')
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_value('GRD Settings', None, 'default_grd_operator')
        if not self.grd_operator_transfer:
            self.grd_operator_transfer = frappe.db.get_value('GRD Settings', None, 'default_grd_operator_transfer')

    def on_update(self):
        self.validate_mandatory_fields_on_update()

    def validate_mandatory_fields_on_update(self):
        if self.workflow_state == 'Under Process':
            field_list = [{'Upload Payment Invoice':'upload_civil_id_payment'}]
            self.set_mendatory_fields(field_list)


    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        self.set_New_civil_id_Expiry_date_in_employee_doctype()
        self.db_set('paci_status',"Completed")
        self.db_set('completed_on', today())
	
    def validate_mandatory_fields_on_submit(self):
        if self.workflow_state == 'Completed':
            field_list = [{'Upload Civil ID':'upload_civil_id'},{'New Civil ID Expiry Date':'new_civil_id_expiry_date'}]
            self.set_mendatory_fields(field_list)

    def set_mendatory_fields(self,field_list):
        mandatory_fields = []
        for fields in field_list:
            for field in fields:
                if not self.get(fields[field]):
                    mandatory_fields.append(field)
        
        if len(mandatory_fields) > 0:
            message= 'Mandatory fields required in Work Permit form<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' + mandatory_field +'</li>'
            message += '</ul>'
            frappe.throw(message)

    def set_New_civil_id_Expiry_date_in_employee_doctype(self):
        """This method to sort records of employee documents upon document name;
           First, get the employee document child table. second, find index of the document. Third, set the new document.
           After that, clear the child table and append the new order"""

        today = date.today()
        Find = False
        employee = frappe.get_doc('Employee', self.employee)
        document_dic = frappe.get_list('Employee Document',fields={'attach','document_name','issued_on','valid_till'},filters={'parent':self.employee})
        for index,document in enumerate(document_dic):
            if document.document_name == "Civil ID":
                Find = True
                break
        if Find:
            document_dic.insert(index,{
                "attach": self.upload_civil_id,
                "document_name": "Civil ID",
                "issued_on":today,
                "valid_till": self.new_civil_id_expiry_date
            })
            employee.set('one_fm_employee_documents',[]) #clear the child table
            for document in document_dic:                # append new arrangements
                employee.append('one_fm_employee_documents',document)

        if not Find:
            employee.append("one_fm_employee_documents", {
            "attach": self.upload_civil_id,
            "document_name": "Civil ID",
            "issued_on":today,
            "valid_till":self.new_civil_id_expiry_date
            })
        employee.civil_id_expiry_date = self.new_civil_id_expiry_date
        employee.save()
    

# Create PACI record once a month for renewals list  
def create_PACI_renewal(preparation_name):
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal' and employee.nationality != 'Kuwaiti':
                create_PACI(frappe.get_doc('Employee',employee.employee),"Renewal",preparation_name)

def create_PACI_for_transfer(employee_name):
    employee = frappe.get_doc('Employee',employee_name)
    if employee:
        create_PACI(frappe.get_doc('Employee',employee.employee),"Transfer")

def create_PACI(employee,Type,preparation_name = None):
        # Create New PACI: 1. New Overseas, 2. New Kuwaiti, 3. Transfer
        if Type == "Renewal":
            start_day = add_days(employee.residency_expiry_date, -14)# MIGHT CHANGE
        if Type == "Transfer":
            start_day = today()
        
        PACI_new = frappe.new_doc('PACI')
        PACI_new.employee = employee.name
        PACI_new.category = Type
        PACI_new.preparation = preparation_name
        PACI_new.date_of_application = start_day
        PACI_new.save()


############################################################################# Reminder Notification 
def notify_operator_to_take_hawiyati_renewal():#cron job at 8pm in working days
    renewal_list=[]
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    paci_list_renewal = frappe.db.get_list('PACI',{'category':'Renewal','workflow_state':"Under Process",'upload_hawiyati':['=','']},['civil_id','name','upload_civil_id_payment_datetime'])
    for paci in paci_list_renewal:
        if date_diff(date.today(),getdate(paci.upload_civil_id_payment_datetime))>=2:
            renewal_list.append(paci)
    email_notification_reminder(renewal_operator,paci_list_renewal,"Reminder","Upload Hawiyati for","Renewal", supervisor)

def notify_operator_to_take_hawiyati_transfer(): #cron job at 8pm in working days
    transfer_list=[]
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
    paci_list_transfer = frappe.db.get_list('PACI',{'category':'Transfer','workflow_state':"Under Process",'upload_hawiyati':['=','']},['civil_id','name','upload_civil_id_payment_datetime'])
    for paci in paci_list_transfer:
        if date_diff(date.today(),getdate(paci.upload_civil_id_payment_datetime))>=2:
            transfer_list.append(paci)
    email_notification_reminder(transfer_operator,paci_list_transfer,"Reminder","Upload Hawiyati for","Transfer", supervisor)

def system_remind_renewal_operator_to_apply():# cron job at 8pm in working days
    """This is a cron method runs every day at 8pm. It gets Draft renewal PACI list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    paci_list = frappe.db.get_list('PACI',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['=',('Renewal')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    notification_reminder(paci_list,supervisor,renewal_operator,"Renewal")
    

def system_remind_transfer_operator_to_apply():# cron job at 8pm in working days
    """This is a cron method runs every day at 4pm. It gets Draft transfer PACI list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
    paci_list = frappe.db.get_list('PACI',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['=',('Transfer')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    notification_reminder(paci_list,supervisor,transfer_operator,"Transfer")
    

def notification_reminder(paci_list,supervisor,operator,type):
    """This method sends first, second, reminders and then send third one and cc supervisor in the email"""
    first_reminder_list=[] 
    second_reminder_list=[] 
    penality_reminder_list=[] 
    if paci_list and len(paci_list) > 0:
        for paci in paci_list:
            if paci.reminder_grd_operator_again:
                penality_reminder_list.append(paci)
            elif paci.reminder_grd_operator and not paci.reminder_grd_operator_again:
                second_reminder_list.append(paci)
            elif not paci.reminder_grd_operator:
                first_reminder_list.append(paci)

    if penality_reminder_list and len(penality_reminder_list)>0:
        email_notification_reminder(operator,penality_reminder_list,"Third Reminder","Apply for",type,supervisor)
    elif second_reminder_list and len(second_reminder_list)>0:
        email_notification_reminder(operator,second_reminder_list,"Second Reminder","Apply for",type)
        for paci in second_reminder_list:
            frappe.db.set_value('PACI',paci.name,'reminder_grd_operator_again',1)
    elif first_reminder_list and len(first_reminder_list)>0:
        email_notification_reminder(operator,first_reminder_list,"First Reminder","Apply for",type)
        for paci in first_reminder_list:
            frappe.db.set_value('PACI',paci.name,'reminder_grd_operator',1)
        
def email_notification_reminder(grd_user,paci_list,reminder_number, action,type, cc=[]):
    """This method send email to the required operator with the list of PACI for applying"""
    message_list=[]
    for paci in paci_list:
        page_link = get_url("/desk#Form/PACI/"+paci.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, paci.civil_id)
        message_list.append(message)

    if message_list:
        message = "<p>{0}: Please {1} {2} PACI listed below</p><ol>".format(reminder_number,action,type)
        for msg in message_list:
            message += "<li>"+msg+"</li>"
        message += "<ol>"
        make(
            subject=_('{0}: {1} {2} PACI'.format(reminder_number,action,type)),
            content=message,
            recipients=[grd_user],
            cc=cc,
            send_email=True,
        )

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

