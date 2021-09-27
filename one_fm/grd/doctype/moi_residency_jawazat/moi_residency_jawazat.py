# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe.utils import today, add_days, get_url
from frappe.core.doctype.communication.email import make
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from one_fm.grd.doctype.paci import paci

class MOIResidencyJawazat(Document):
    def validate(self):
        self.set_grd_values()
        self.set_company_address()
        self.set_company_unified_number()
        self.set_paci_number()
	
    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_value('GRD Settings', None, 'default_grd_supervisor')
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_value('GRD Settings', None, 'default_grd_operator')
    
    def set_company_address(self):
        """This method sets the company address from MOCI document"""
        missing_field = False
        fields = ['company_pam_file_number','company_location','company_block_number','company_street_name','company_building_name','company_contact_number']
        for field in fields:
            if not self.get(field):
                missing_field = True
        if missing_field:
            moci = frappe.get_doc('MOCI','ONE Facilities Management Company W.L.L.')
            self.company_location = moci.city
            self.company_block_number = moci.blook
            self.company_street_name = moci.street
            self.company_building_name = moci.building
            self.company_pam_file_number = moci.company_civil_id

    def set_company_unified_number(self):
        """This method to set the unified number from private pam file to moi document"""
        if not self.company_centralized_number:
            number = frappe.db.get_value('PAM File',{'pam_file_number':self.company_pam_file_number},['company_unified_number'])
        if number:
            self.company_centralized_number = number

    def set_paci_number(self):
        """This method sets the paci number in moi document from pam authorized signatury under same file"""
        if not self.paci_number:
            paci_number = frappe.db.get_value('PAM Authorized Signatory List',{'pam_file_number':self.company_pam_file_number},['company_paci_number'])
            self.paci_number = paci_number

    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        self.set_residency_expiry_new_date_in_employee_doctype()
        self.db_set('completed_on', now_datetime())
        if self.category == "Transfer":
            self.recall_create_paci()

    def recall_create_paci(self):
        paci.create_PACI_for_transfer(self.employee)

    def validate_mandatory_fields_on_submit(self):
        field_list = [{'Upload Payment Invoice':'invoice_attachment'},{'Upload Residency':'residency_attachment'},{'Updated Residency Expiry Date':'new_residency_expiry_date'}]
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

    def set_residency_expiry_new_date_in_employee_doctype(self):
        """This method to sort records of employee documents upon document name;
           First, get the employee document child table. second, find index of the document. Third, set the new document.
           After that, clear the child table and append the new order"""

        today = date.today()
        Find = False
        employee = frappe.get_doc('Employee', self.employee)
        document_dic = frappe.get_list('Employee Document',fields={'attach','document_name','issued_on','valid_till'},filters={'parent':self.employee})
        for index,document in enumerate(document_dic):
            if document.document_name == "Residency Expiry Attachment":
                Find = True
                break
        if Find:
            document_dic.insert(index,{
                "attach": self.residency_attachment,
                "document_name": "Residency Expiry Attachment",
                "issued_on":today,
                "valid_till": self.new_residency_expiry_date
            })
            employee.set('one_fm_employee_documents',[]) #clear the child table
            for document in document_dic:                # append new arrangements
                employee.append('one_fm_employee_documents',document)

        if not Find:
            employee.append("one_fm_employee_documents", {
            "attach": self.residency_attachment,
            "document_name": "Residency Expiry Attachment",
            "issued_on":today,
            "valid_till":self.new_residency_expiry_date
            })
        employee.work_permit_expiry_date = self.new_residency_expiry_date
        employee.save()
            
#fetching the list of employee has Extend and renewal status from HR list. 
def set_employee_list_for_moi(preparation_name):
    # filter work permit records only take the non kuwaiti 
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal' and employee.nationality != 'Kuwaiti':# For renewals
                create_moi_record(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)
            if employee.renewal_or_extend != 'Renewal' and employee.nationality != 'Kuwaiti':# For extend
                create_moi_record(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)

# Creat moi for transfer
def creat_moi_for_transfer(work_permit_name):
    work_permit = frappe.get_doc('Work Permit',work_permit_name)
    if work_permit:
        employee = frappe.get_doc('Employee',work_permit.employee)
        if employee:
            create_moi_record(frappe.get_doc('Employee',employee.employee),"Transfer")

def create_moi_record(employee,Renewal_or_Extend,preparation_name = None):
    
    if Renewal_or_Extend == "Renewal":
        category = "Renewal"
        start_date = add_days(employee.residency_expiry_date, -14)
    if Renewal_or_Extend == "Transfer":
        category = "Transfer"
        start_date = today()
    if Renewal_or_Extend != "Renewal" and Renewal_or_Extend != "Transfer":
        category = "Extend"
        start_date = add_days(employee.residency_expiry_date, -7)
        

    # start_day_for_renewal = add_days(employee.residency_expiry_date, -14)# MIGHT CHANGE IN TRANSFER
    new_moi = frappe.new_doc('MOI Residency Jawazat')
    new_moi.employee = employee.name
    new_moi.preparation = preparation_name
    new_moi.renewal_or_extend = Renewal_or_Extend
    new_moi.date_of_application = start_date
    new_moi.category = category
    new_moi.insert()

############################################################################# Reminder Notification 
def system_remind_renewal_operator_to_apply():# cron job at 4pm
    """This is a cron method runs every day at 4pm. It gets Draft renewal MOI list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    moi_list = frappe.db.get_list('MOI Residency Jawazat',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['in',('Renewal','Extend')]},
    ['one_fm_civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])
    notification_reminder(moi_list,supervisor,renewal_operator,"Renewal or Extend")
   

def system_remind_transfer_operator_to_apply():# cron job at 4pm
    """This is a cron method runs every day at 4pm. It gets Draft transfer MOI list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator_transfer")
    moi_list = frappe.db.get_list('MOI Residency Jawazat',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['=',('Transfer')]},
    ['one_fm_civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])
    notification_reminder(moi_list,supervisor,transfer_operator,"Local Transfer")
    
    
def notification_reminder(moi_list,supervisor,operator,type):
    """This method sends first, second, reminders and then send third one and cc supervisor in the email"""
    first_reminder_list=[] 
    second_reminder_list=[] 
    penality_reminder_list=[] 
    if moi_list and len(moi_list) > 0:
        for moi in moi_list:
            if moi.reminded_grd_operator_again:
                penality_reminder_list.append(moi)
            elif moi.reminded_grd_operator and not moi.reminded_grd_operator_again:
                second_reminder_list.append(moi)
            elif not moi.reminded_grd_operator:
                first_reminder_list.append(moi)

    if penality_reminder_list and len(penality_reminder_list)>0:
        email_notification_reminder(operator,penality_reminder_list,"Third Reminder","Apply for",type,supervisor)
    elif second_reminder_list and len(second_reminder_list)>0:
        email_notification_reminder(operator,second_reminder_list,"Second Reminder","Apply for",type)
        for moi in second_reminder_list:
            frappe.db.set_value('MOI Residency Jawazat',moi.name,'reminded_grd_operator_again',1)
    elif first_reminder_list and len(first_reminder_list)>0:
        email_notification_reminder(operator,first_reminder_list,"First Reminder","Apply for",type)
        for moi in first_reminder_list:
            frappe.db.set_value('MOI Residency Jawazat',moi.name,'reminded_grd_operator',1)
        
def email_notification_reminder(grd_user,moi_list,reminder_number, action,type, cc=[]):
    """This method send email to the required operator with the list of MOI Residency Jawazat for applying"""
    message_list=[]
    for moi in moi_list:
        page_link = get_url("/desk#Form/MOI Residency Jawazat/"+moi.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, moi.civil_id)
        message_list.append(message)

    if message_list:
        message = "<p>{0}: Please {1} {2} MOI Residency Jawazat listed below</p><ol>".format(reminder_number,action,type)
        for msg in message_list:
            message += "<li>"+msg+"</li>"
        message += "<ol>"
        make(
            subject=_('{0}: {1} {2} MOI Residency Jawazat'.format(reminder_number,action,type)),
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



