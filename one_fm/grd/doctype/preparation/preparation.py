
# class Preparation(Document):
# 	pass
# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe.utils import cstr
from frappe.utils import datetime
from frappe.utils import nowdate
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url#extra
from datetime import date, timedelta
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import get_datetime, add_to_date, getdate
from one_fm.grd.doctype.work_permit import work_permit
from one_fm.grd.doctype.medical_insurance import medical_insurance
from one_fm.grd.doctype.residency_payment_request import residency_payment_request


class Preparation(Document):
    def validate(self):
        self.set_values()

    def set_values(self):
        # if not self.hr_user:
        #   self.hr_user = frappe.db.get_value('GRD Settings', None, 'default_grd_supervisor')
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_value('GRD Settings', None, 'default_grd_operator')
    #pass
    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        self.db_set('submitted_by', frappe.session.user)
        self.db_set('submitted_on', today())
        self.recall_create_work_permit_renewal() ## create work permit record for renewals
        self.recall_create_medical_insurance_renewal() ## create medical insurance record for renewals
        self.recall_create_residency_payment_request_renewal()
        #self.notify_finance_department()
        #notify_request_for_renewal_or_extend()

    def validate_mandatory_fields_on_submit(self):
        field_list = [{'Renewal or extend':'renewal_or_extend'}, {'Preparation Record':'preparation_record'}]
        
        mandatory_fields = []
        mandatory_fields_reqd = False
        for item in self.rpr_list:#each item in the rpr list row
            if not item.renewal_or_extend:#column not filled
                mandatory_fields_reqd = True
                mandatory_fields.append(item.idx)


        if len(mandatory_fields) > 0:
            message = 'Mandatory fields required in Preparation to Submit<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' +'<p> fill the renewal or extend field </p>'+ str(mandatory_field) +'</li>'
            message += '</ul>'
            frappe.throw(message)

        if self.hr_approval == "No":
            frappe.throw("Must be approved by the HR")

    def recall_create_work_permit_renewal(self):
        work_permit.create_work_permit_renewal()
    
    def recall_create_medical_insurance_renewal(self):
        medical_insurance.valid_work_permit_exists()
    
    def recall_create_residency_payment_request_renewal(self):
        residency_payment_request.create_residency_payment_request()

    # def recall_create_moi_extend(self):
    #   self.


# def notify_finance_department(): # Notify the finance department
#   reminder_indicator = "yellow"
#   filters = {'docstatus': 1, 'hr_approval': 'Yes'}
#   # preparation_list = frappe.db.get_list('Preparation', filters, ['name', 'notify_finance_user'])
#   # print(preparation_list)
#   preparation_list = frappe.get_doc('Preparation', filters, ['name', 'notify_finance_user'])
#   print(preparation_list.name)
#       # if self.hr_approval:
#   page_link = get_url("http://192.168.8.105/desk#Form/Preparation/" + preparation_list.name)
#   message = "<p>Please Review the list <a href='{0}'>{1}</a> Submitted by {2}.</p>".format(page_link, preparation_list.name, preparation_list.submitted_by)
#   subject = 'Request by {0} for preparing the amount'.format(preparation_list.submitted_by)
#   #send_email(preparation_list, [preparation_list.hr_approval], message, subject)
#   create_notification_log(subject, message, [preparation_list.hr_approval], preparation_list)
    
#   # print(preparation_list)
#   # create_notification_log(subject, message, [preparation_list.notify_finance_user], preparation_list)
#   #email_notification_to_grd_user('notify_finance_user', preparation_list, reminder_indicator, 'Take action on Payment Transfer Requested for ')

    

def create_preparation():
    doc = frappe.new_doc('Preparation')
    doc.posting_date = nowdate()
    today = date.today()
    first_day = today.replace(day=1) + relativedelta(months=1)
    last_day = first_day.replace(day=calendar.monthrange(first_day.year, first_day.month)[1])
    get_employee_entries(doc,first_day,last_day)
    #notify_grd_operator()
    #notify_request_for_renewal_or_extend()
    #############recall_create_work_permit_renewal().  =>test it on submit
    # doc.save(ignore_permission=True)

def get_employee_entries(doc,first_day,last_day):

    # Test other solution than sql #
    employee_entries = frappe.db.get_list('Employee',
                            filters={
                                'residency_expiry_date': ['between',(first_day,last_day)],
                                'status': 'Active'
                            },
                            )

    doc.set("preparation_record", [])
    for d in employee_entries:
        #print(d.name)#for testing purpuses
        doc.append("preparation_record", {
            "employee": d.name
        })
    doc.save()

def notify_request_for_renewal_or_extend():

    filters1 = {'docstatus': 1, 
                'hr_approval': ['=', "Yes"]}
    preparation_list = frappe.get_doc('Preparation', filters1,['name', 'grd_operator','grd_supervisor'])
    
    page_link = get_url("http://192.168.8.105/desk#Form/Preparation/"+preparation_list.name)
    message = "<p>Please Review the Renewal and Extend List of employee <a href='{0}'></a></p>".format(page_link, preparation_list.name)
    subject = '{0} Renewal and Extend list approved'.format("Fill")
    send_email(preparation_list, [preparation_list.grd_operator], message, subject)
    create_notification_log(subject, message, [preparation_list.grd_operator], preparation_list)

# def recall_create_work_permit_renewal():
#   #work_permit.work_permit.create_work_permit_renewal() # call the method
#   work_permit.create_work_permit_renewal()

def notify_grd_operator(): # Need to call create work permit from here!!  import work permit file
    reminder_indicator = 'yellow'
    # Get work permit list
    filters1 = {'docstatus': 1, 'hr_approval': 'Yes'}
    filter2 = {'renewal_or_extend':['=','Renewal']}# will notify all renewal list for creating work permit
    preparation_list = frappe.get_doc('Preparation', filters1,['name', 'grd_operator','grd_supervisor'])
    #renewal_list = frappe.get_doc('RPR List',filter2)
    print(preparation_list.name)#will get the last pre rpr list
    #print(renewal_list.name)
    email_notification_to_grd_user('grd_operator', preparation_list, reminder_indicator, 'Approve')


def email_notification_to_grd_user(grd_user, preparation_list, reminder_indicator, action):
#def email_notification_to_grd_user(grd_user, preparation, reminder_indicator, action):
    recipients = {}

    for preparation in preparation_list:

        page_link = get_url("http://192.168.8.105/desk#Form/Preparation/"+preparation.name)
        message = "<a href='{0}'>{1}</a>".format(page_link, preparation.name)
        if preparation[grd_user] in recipients:
            recipients[preparation[grd_user]].append(message)#add the message in the empty list
        else:
            recipients[preparation[grd_user]]=[message]

    if recipients:
        for recipient in recipients:
            subject = 'Preparation {0}'.format(preparation.name)#added
            message = "<p>Please {0} Preparation listed below</p><ol>".format(action)
            for msg in recipients[recipient]:
                message += "<li>"+msg+"</li>"
            message += "<ol>"
            # frappe.sendmail(
            #   recipients=[recipient],
            #   cc=cc,
            #   subject=_('{0} Preparation'.format(action)),
            #   message=message,
            #   header=['Work Permit Reminder', reminder_indicator],
            # )
            to_do_to_grd_users(_('{0} Preparation'.format(action)), message, recipient)
            print(preparation[grd_user])
            for preparation in preparation_list:
                print(preparation)
            create_notification_log(subject, message, [work_permit.grd_user], self)#added

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