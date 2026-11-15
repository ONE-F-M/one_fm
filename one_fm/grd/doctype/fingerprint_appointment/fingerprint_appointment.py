# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date
from one_fm.api.notification import create_notification_log
from one_fm.utils import send_push_notification
from frappe.model.document import Document
from frappe.utils import today, get_url, date_diff, getdate, format_datetime
from one_fm.grd.doctype.medical_insurance import medical_insurance
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from one_fm.processor import sendemail
from one_fm.operations.doctype.operations_shift.operations_shift import get_shift_supervisor_user


class FingerprintAppointment(Document):

    def before_save(self):
        self.set_gr_operator()

    def set_gr_operator(self):
        if self.is_new() and not self.government_relations_operator:
            self.db_set('government_relations_operator', frappe.session.user)

    # The Fingerprint Appointment Lifecycle process checks the pickup details and the
    # appointment date in its script tasks before it moves the record on.

    def before_one_day_of_appointment_date(self):
        today = date.today()
        if date_diff(getdate(self.date_and_time_confirmation),today) == -1 and self.preparing_documents == "No":
            self.notify_operator_to_prepare_for_fp()


    def notify_site_supervisor(self):
        """Notify site supervisor with the employee's appointment"""
        site = frappe.db.get_value("Employee",{'one_fm_civil_id':self.civil_id},['site'])
        if site:
            site_doc = frappe.get_doc("Operations Site",site)
            if site_doc:
                employee = frappe.get_doc("Employee", site_doc.site_supervisor)
                send_email_notification(self, [employee.user_id])

    def notify_shift_supervisor(self):
        """Notify shift supervisor with the employee's appointment"""
        shift = frappe.db.get_value("Employee",{"one_fm_civil_id":self.civil_id},"shift")
        if shift:
            shift_supervisor_user = get_shift_supervisor_user(shift)
            if shift_supervisor_user:
                send_email_notification(self, [shift_supervisor_user])

    @property
    def fetch_appointment_date(self):
        return get_datetime(self.date_and_time_confirmation).date()
        
    
def before_one_day_of_appointment_date():
    today = date.today()
    query = frappe.db.sql("""
        SELECT name FROM `tabFingerprint Appointment`
        WHERE
        DATEDIFF(date_and_time_confirmation, '{today}')=-1 AND preparing_documents='No'
    """, as_dict=1)
    for row in query:
        frappe.get_doc("Fingerprint Appointment", row.name).notify_operator_to_prepare_for_fp()

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
        "role":"Government Relations Operator",
        "reference_type":"Fingerprint Appointment"
    }).insert(ignore_permissions=True)

def send_email_notification(doc, recipients):
	page_link = get_url(doc.get_url())
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
        frappe.get_doc({
            'doctype': 'Notification Log',
            'subject': subject,
            'email_content': message,
            'for_user': user,
            'document_type': 'Fingerprint Appointment',
            'document_name': reference_doc.name,
            'from_user': reference_doc.modified_by
        }).insert(ignore_permissions=True)




def notify_supervisor_of_pending_fingerprint_appointment():
    appointments = frappe.db.sql("""
        SELECT 
            fa.name,
            fa.employee_supervisor,
            fa.employee,
            fa.modified_by,
            COALESCE(e.employee_name, fa.employee) as employee_name
        FROM `tabFingerprint Appointment` fa
        LEFT JOIN `tabEmployee` e ON fa.employee = e.name
        WHERE fa.workflow_state = 'Pending Supervisor'
    """, as_dict=1)
    
    for obj in appointments:
        if obj.employee_supervisor:
            create_notification_log(
                subject=f'Reminder: Action Required on Fingerprint Appointment for {obj.employee_name}',
                message=f'Reminder: You need to take action on {get_link_to_form("Fingerprint Appointment", obj.name, label="Fingerprint Appointment")} for {obj.employee_name}.',
                for_users=[obj.employee_supervisor],
                reference_doc=obj
            )