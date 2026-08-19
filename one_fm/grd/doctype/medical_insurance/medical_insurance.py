# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, get_url,getdate, get_year_start
from frappe import _
from datetime import date
from frappe.core.doctype.communication.email import make
from frappe.utils import now_datetime
from one_fm.grd.doctype.residency_payment_request import residency_payment_request
from one_fm.grd.doctype.residency import residency
from one_fm.processor import sendemail
from one_fm.utils import is_scheduler_emails_enabled

class MedicalInsurance(Document):
    def before_insert(self):
        self.cancel_existing()
    
    def cancel_existing(self):
        """Cancel  documents for that employee which were created in previous years"""
        year_threshold = getdate(self.date_of_application).year or getdate().year
        first_day_of_year = getdate(f'01-01-{year_threshold}') #Get the first day of the year
        existing_docs = frappe.get_all(self.doctype,{'date_of_application':['<',first_day_of_year],'name':['!=',self.name],'docstatus':0,'employee':self.employee})
        if existing_docs:
            for one in existing_docs:
                frappe.db.set_value(self.doctype,one,'workflow_state','Cancelled')
            frappe.db.commit()

    def validate(self):
        self.set_value()

    def set_value(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")

    def on_submit(self):
        self.set_depend_on_fields()
        self.db_set('medical_insurance_submitted_by', frappe.session.user)
        self.db_set('medical_insurance_submitted_on', now_datetime())
        if self.insurance_status == "Local Transfer":
            self.recall_create_moi_transfer()

    def recall_create_moi_transfer(self):
        residency.create_moi_for_transfer(self.work_permit)


    def set_depend_on_fields(self):
        if self.upload_medical_insurance is None:
            frappe.throw(_('You need to upload the Medical Insurance document before you can mark this record as “Done”.'))


def valid_work_permit_exists(preparation_name):
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal (Non-Kuwaiti)' and employee.nationality != 'Kuwaiti':
                try:
                    create_mi_record(frappe.get_doc('Work Permit',{'preparation':preparation_name,'employee':employee.employee}))
                except Exception as e:
                    frappe.log_error(message=frappe.get_traceback(), title=f"Error creating Medical Insurance for Work Permit of employee {employee.employee} in Preparation {preparation_name}")
                    continue

#Creating mi for transfer
def creat_medical_insurance_for_transfer(employee_name):
    employee = frappe.get_doc('Employee',employee_name)
    if employee:
        if transfer_insurance_already_open(employee.name):
            return
        # The employee's latest transfer permit, not whichever Work Permit the filter
        # happened to return first - that could be a renewal from years ago, which has no
        # insurance status to open a policy under.
        create_mi_record(frappe.get_last_doc('Work Permit', filters={
            'employee': employee.employee,
            'work_permit_type': 'Local Transfer',
        }))


def transfer_insurance_already_open(employee):
    """Is there already a Local Transfer policy open for this employee this year?

    A Preparation opens the whole set of documents up front (WI-001824) and the Work
    Permit reaching Completed asks for one as well, so without this the employee ends up
    insured twice for the same transfer. Scoped to the current year to match
    cancel_existing, so a genuine second transfer in a later year is still a new record.
    """
    return bool(frappe.get_all('Medical Insurance', limit=1, filters={
        'employee': employee,
        'insurance_status': 'Local Transfer',
        'date_of_application': ['>=', get_year_start(today())],
        'workflow_state': ['!=', 'Cancelled'],
        'docstatus': ['<', 2],
    }))


# WI-002098: the state a new policy opens in. An overseas hire's insurance is paid for on
# the provider's portal before there is anything for the PRO to apply for, so it is held in
# Draft until the GR Operator has done that and hands it on.
#
# Every other policy - a renewal, a local transfer - goes straight to the PRO, the way it
# did before Draft existed. Named here rather than left to the workflow's first state,
# because Draft is now that first state and would otherwise become the default for all of
# them.
DRAFT = "Draft"
APPLY_ONLINE_BY_PRO = "Apply Online by PRO"
OVERSEAS_WORK_PERMIT_TYPES = ("Overseas", "Overseas (Government)")


def initial_workflow_state(work_permit_type):
	"""Where a policy opened against this kind of Work Permit starts (WI-002098)."""
	return DRAFT if work_permit_type in OVERSEAS_WORK_PERMIT_TYPES else APPLY_ONLINE_BY_PRO


def create_mi_record(WorkPermit, insurance_status=None):
    """Open the insurance a Work Permit calls for.

    WI-002033: a caller that already knows the classification - a Preparation row, whose
    Action states it in NEW_ACTION_DOCUMENTS - passes it in. The derivation below is kept
    for the callers that do not: the transfer path and the renewal path arrive with a Work
    Permit and nothing else.
    """
    new_medical_insurance = frappe.new_doc('Medical Insurance')

    if insurance_status:
        Insurance_status = insurance_status
        # The application date still follows the Work Permit's, which is the fact the
        # caller does not have and this function does.
        new_medical_insurance.date_of_application = (
            today() if insurance_status == "Local Transfer" else WorkPermit.date_of_application
        )
    elif(WorkPermit.work_permit_type == "Renewal Non Kuwaiti"):
        Insurance_status = "Renewal"
        new_medical_insurance.date_of_application = WorkPermit.date_of_application #setting the same date of application of wp
    elif(WorkPermit.work_permit_type in ("Overseas", "Overseas (Government)")):
        # An overseas hire has no insurance yet, so the policy is opened as New
        # (WI-001881). Applied for the day the Work Permit was, which for an Overseas
        # Work Permit is the day its Preparation was submitted.
        #
        # A government-contract hire is the same insurance (WI-002024): the file the work
        # permit was raised against changes its fee, not whether the employee is insured.
        Insurance_status = "New"
        new_medical_insurance.date_of_application = WorkPermit.date_of_application
    elif (WorkPermit.work_permit_type == "Local Transfer"):#for non kuwaiti <if it is for kuwait called new or renew and they don't have MI process
        Insurance_status = "Local Transfer" # the Insurance_status will be new for overseas only
        new_medical_insurance.date_of_application = today() #set the date of creation
    else:
        # Kuwaitis have no Medical Insurance process at all, so reaching here means a
        # caller asked for one against a Work Permit type that does not have a status to
        # open it under. Better to say so than to insert a row with a blank status.
        frappe.throw(_("Medical Insurance cannot be opened for a {0} Work Permit ({1}).").format(
            WorkPermit.work_permit_type, WorkPermit.name))

    new_medical_insurance.work_permit = WorkPermit.name
    new_medical_insurance.preparation = WorkPermit.preparation
    new_medical_insurance.insurance_status = Insurance_status
    new_medical_insurance.passport_expiry_date = WorkPermit.passport_expiry_date
    new_medical_insurance.employee_id = WorkPermit.employee_id
    new_medical_insurance.employee = WorkPermit.employee
    new_medical_insurance.insert()

    # Written after the insert rather than before it. Frappe reads a workflow_state set on
    # a new document as a transition out of the workflow's first state and refuses one the
    # session's user holds no role for - and these are opened by the system on behalf of a
    # Preparation, so there is no operator in the session to make it. PACI hands its
    # overseas applications to the PRO the same way.
    initial_state = initial_workflow_state(WorkPermit.work_permit_type)
    if initial_state != new_medical_insurance.workflow_state:
        new_medical_insurance.db_set("workflow_state", initial_state)

    return new_medical_insurance

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
    {'date_of_application':['<=',today()],'workflow_state':'Apply Online by PRO','insurance_status':['in',('Renewal','New')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    
    if is_scheduler_emails_enabled():
        notification_reminder(medical_insurance_list,supervisor,renewal_operator,"Renewal or New")


def system_remind_transfer_operator_to_apply_mi():
    """
    This is a cron method runs every day at 8am. It gets Draft `transfer` Medical Insurance list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
    medical_insurance_list = frappe.db.get_list('Medical Insurance',
    {'date_of_application':['<=',today()],'workflow_state':'Apply Online by PRO','insurance_status':['=',('Local Transfer')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])
    
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
