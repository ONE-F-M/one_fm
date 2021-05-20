# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_years
from frappe.utils import today, add_days, get_url
from frappe import _
from frappe.utils.user import get_users_with_role
from frappe.permissions import has_permission
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr


class MedicalInsurance(Document):
    
    def validate(self):
        self.set_value()
        #self.valid_work_permit_exists()
        self.update_end_date()
        self.validate_no_of_application()

    def set_value(self):
        if not self.grd_supervisor: 
            self.grd_supervisor = frappe.db.get_single_value("GRD Settings", "default_grd_supervisor")
        if not self.grd_operator: 
            self.grd_operator = frappe.db.get_single_value("GRD Settings", "default_grd_operator")
    
    def on_submit(self):
        self.set_depend_on_fields()
        self.db_set('completed','Yes')
        self.db_set('medical_insurance_submitted_by', frappe.session.user)
        self.db_set('medical_insurance_submitted_on', today())
    
    def set_depend_on_fields(self):
        if self.apply_medical_insurance_online == "No":
            frappe.throw(_('Apply Medical Insurance Online Required To Submit'))
        elif self.submission_of_application == "No":
            frappe.throw(_('Submission of Application Is Required To Submit'))
        elif self.upload_medical_insurance == None:
            frappe.throw(_('Upload Medical Insurance Is Required To Submit'))

    def validate_no_of_application(self):#### wont be used as all the records are indivitual
        if self.category == "Group" and len(self.items) > 20:
            frappe.throw(_("More than 20 Application is not Possible"))

    def update_end_date(self): # Set the value of end date
        if self.category == 'Individual' and self.no_of_years and int(self.no_of_years) > 0 and self.start_date:
            self.end_date = add_years(self.start_date, self.no_of_years)
        elif self.category == 'Group':
            for item in self.items:
                if item.no_of_years and item.no_of_years > 0 and item.start_date:
                    item.end_date = add_years(item.start_date, item.no_of_years)


#need to be inside the class
def valid_work_permit_exists(preparation_name):
    # TODO: filter work permit records only take the non kuwaiti
    
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal' and employee.nationality != 'Kuwaiti':
                print(employee.employee)
                create_mi_record(frappe.get_doc('Work Permit',{'preparation':preparation_name,'employee':employee.employee}))
        
def create_mi_record(WorkPermit):

    if(WorkPermit.work_permit_type == "Renewal Non Kuwaiti"):
        Insurance_status = "Renewal"
    elif(WorkPermit.work_permit_type == "New Non Kuwaiti"):#Overseas
        Insurance_status = "New" 
    elif (WorkPermit.work_permit_type == "Local Transfer"):#for non kuwaiti <if it is for kuwait called new or renew and they don;t have MI process
        Insurance_status = "Local Transfer" # the Insurance_status will be new for overseas only 

    new_medical_insurance = frappe.new_doc('Medical Insurance')
    new_medical_insurance.work_permit = WorkPermit.name
    new_medical_insurance.preparation = WorkPermit.preparation
    new_medical_insurance.insurance_status = Insurance_status
    new_medical_insurance.insert()
# Notify grd operatorwith the created mi dt
    #notify_grd_operator_draft_new_mi()

@frappe.whitelist()
def get_employee_data_from_civil_id(civil_id):
    employee_id = frappe.db.exists('Employee', {'one_fm_civil_id': civil_id})
    if employee_id:
        return frappe.get_doc('Employee', employee_id)

@frappe.whitelist()
def set_dates():
    currentDateTime = now_datetime()
    return currentDateTime


def notify_grd_operator_draft_new_mi():
    filter_mi = {'apply_medical_insurance_online': ['=', "No"],'docstatus':0 }
    mi = frappe.get_doc('Medical Insurance',filter_mi)
    page_link = get_url("/desk#Form/Medical Insurance/"+mi.name)
    message = "<p>Please fill the medical insurance form for employee <a href='{0}'>{1}</a></p>".format(page_link, mi.name)
    subject = '{0} Medical Insurance form'.format("Apply")
    send_email(mi, [mi.grd_operator], message, subject)
    create_notification_log(subject, message, [mi.grd_operator], mi)
    
def notify_grd_supervisor_to_submit_on_system():
    notify_grd_supervisor_submit_mi_on_system('yellow')

def notify_grd_operator_to_mark_completed_first():#for the first time 9:00 am (cron)
    notify_grd_operator_to_mark_mi_complete('yellow')

def notify_grd_operator_to_mark_completed_second():#for the second time 9:30am (cron)
    notify_grd_operator_to_mark_mi_complete('red')


def notify_grd_supervisor_submit_mi_on_system(reminder_indicator):
    filter_mi = {'apply_medical_insurance_online': ['=', "Yes"],
                 'submission_of_application':['=',"No"]
                }
    mi_list = frappe.get_list('Medical Insurance',filter_mi, ['name', 'grd_supervisor'])
    cc = [mi_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_supervisor', mi_list, reminder_indicator, 'Submit',cc)

# Notify grd operator to mark mi as completed on the system (first time)
def notify_grd_operator_to_mark_mi_complete(reminder_indicator):
    filter_mi = {'apply_medical_insurance_online': ['=', "Yes"],
                 'submission_of_application':['=',"Yes"],
                 'upload_medical_insurance':['!=', " "]
                }
    mi_list = frappe.get_list('Medical Insurance',filter_mi, ['name', 'grd_operator'])
    cc = [mi_list[0].grd_supervisor] if reminder_indicator == 'red' else []
    email_notification_to_grd_user('grd_operator', mi_list, reminder_indicator, 'Completed',cc)

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