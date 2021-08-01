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
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from one_fm.grd.doctype.paci import paci

class MOIResidencyJawazat(Document):
    def validate(self):
        self.set_grd_values()
	
    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_value('GRD Settings', None, 'default_grd_supervisor')
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_value('GRD Settings', None, 'default_grd_operator')
    
    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        self.set_residency_expiry_new_date_in_employee_doctype()
        self.db_set('completed_on', now_datetime())
        if self.category == "Transfer":
            self.recall_create_paci()

    def recall_create_paci(self):
        paci.create_PACI_for_transfer(self.employee)

    def validate_mandatory_fields_on_submit(self):
        if not self.invoice_attachment:
            frappe.throw(_("Attach The Invoice To Submit"))
        if not self.residency_attachment:
            frappe.throw(_("Attach Residency To Submit"))
        if not self.new_residency_expiry_date:
            frappe.throw(_("Add The New Residency Expiry Date To Submit"))

    def set_residency_expiry_new_date_in_employee_doctype(self):
        today = date.today()
        employee = frappe.get_doc('Employee', self.employee)
        employee.residency_expiry_date = self.new_residency_expiry_date # update the date of expiry
        employee.append("one_fm_employee_documents", {
            "attach": self.residency_attachment,
            "document_name": "Residency Expiry Attachment",
            "issued_on":today,
            "valid_till":self.new_residency_expiry_date
        })
        employee.save()
            
#fetching the list of employee has Extend and renewal status from HR list.  =====> to create moi record
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

# Run this method at 4 pm (cron)
def system_checks_grd_operator_apply_online():
    filters = {'docstatus': 0,'date_of_application':['<=',today()]}
    moi_list = frappe.db.get_list('MOI Residency Jawazat', filters, ['name', 'grd_operator'])
    if len(moi_list) > 0:
        moi_notify_first_grd_operator()

# Notify GRD Operator at 9:00 am (cron)
def moi_notify_first_grd_operator():
    moi_notify_grd_operator('yellow')

# Notify GRD Operator at 9:30 am (cron)
def moi_notify_again_grd_operator():
    moi_notify_grd_operator('red')

def moi_notify_grd_operator(reminder_indicator):
    # Get moi list
    today = date.today()
    filters = {'docstatus': 0,
    'date_of_application':['<=',today()] ,'reminded_grd_operator': 0, 'reminded_grd_operator_again':0}
    if reminder_indicator == 'red':
        filters['reminded_grd_operator'] = 1
        filters['reminded_grd_operator_again'] = 0
                                                            
    moi_list = frappe.db.get_list('MOI Residency Jawazat', filters, ['name', 'grd_operator'])
    # send grd supervisor if reminder for second time (red)
    cc = [moi_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_operator', moi_list, reminder_indicator, 'Submit', cc)

def email_notification_to_grd_user(grd_user, moi_list, reminder_indicator, action, cc=[]):
    recipients = {}

    for moi in moi_list:
        page_link = get_url("http://192.168.8.102/desk#Form/MOI Residency Jawazat/"+moi.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, moi.name)
        if moi[grd_user] in recipients:
            recipients[moi[grd_user]].append(message)#add the message in the empty list
        else:
            recipients[moi[grd_user]]=[message]

    if recipients:
        for recipient in recipients:
            subject = 'MOI Residency Jawazat  {0}'.format(moi.name)#added
            message = "<p>Please {0} MOI Residency Jawazat listed below</p><ol>".format(action)
            for msg in recipients[recipient]:
                message += "<li>"+msg+"</li>"
            message += "<ol>"
            frappe.sendmail(
                recipients=[recipient],
                cc=cc,
                subject=_('{0} MOI Residency Jawazat'.format(action)),
                message=message,
                header=['MOI Residency Jawazat Reminder', reminder_indicator],
            )
            to_do_to_grd_users(_('{0} MOI Residency Jawazat'.format(action)), message, recipient)
            create_notification_log(subject, message, [moi.grd_user], moi)#added

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



