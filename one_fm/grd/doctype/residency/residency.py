# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe.utils import get_url
from frappe.core.doctype.communication.email import make
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from one_fm.utils import is_scheduler_emails_enabled
from one_fm.grd.processa import cancel_processes

class Residency(Document):
    company = frappe.db.get_value("Company", frappe.defaults.get_global_default('company'), 
            ['phone_no', 'email', 'company_name_arabic'], as_dict=1)
    
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
            cancel_processes(self.doctype, existing_docs, _("Replaced by a newer Residency"))
            frappe.db.commit()

    
    def validate(self):
        self.set_grd_values()
        self.set_new_expiry_date()
        self.set_company_address()
        self.set_company_unified_number()
        self.set_paci_number()
        self.clear_unticked_exception_details()
        self.validate_exception_details()

    def clear_unticked_exception_details(self):
        """Empty an exception's details when its box is unticked (WI-002105).

        The fields are hidden when the box is off, so anything left in them is invisible -
        and a Damj letter or a fine receipt still attached to a record that no longer claims
        either would go on reaching the costing and the print format. The fine amount goes
        back to zero rather than blank, because it is a Currency the totals add up.

        Cleared here rather than only in the browser: a record can be unticked by a data
        import, a patch or the API, none of which run the form's handlers.
        """
        if not self.damj_is_applicable:
            self.original_civil_id = None
            self.upload_damj_letter = None
            self.upload_damj_letter_on = None

        if not self.residency_fine_to_be_added:
            self.residency_fine_amount_kwd = 0
            self.upload_residency_fine_payment_receipt = None
            self.upload_residency_fine_payment_receipt_on = None

    def validate_exception_details(self):
        """Hold the save until a ticked exception carries its evidence (WI-002022).

        On `validate` rather than `on_submit` because the story blocks the save, not
        only the completion: a Damj or a fine recorded without the government letter or
        the payment receipt is not a record of anything, and letting one sit in Draft
        that way means the operator finds out at the end of the process instead of the
        moment they tick the box.

        A fine amount of 0 counts as missing. Ticking "Residency Fine to be Added" and
        then entering nothing is the mistake the check exists to catch, and a zero-value
        fine has nothing for finance to reference.
        """
        field_list = []

        if self.damj_is_applicable:
            field_list += [
                {'Original Civil ID': 'original_civil_id'},
                {'Upload DAMJ Letter': 'upload_damj_letter'},
            ]

        if self.residency_fine_to_be_added:
            field_list += [
                {'Residency Fine Amount (KWD)': 'residency_fine_amount_kwd'},
                {'Upload Residency Fine Payment Receipt': 'upload_residency_fine_payment_receipt'},
            ]

        if field_list:
            self.set_mendatory_fields(field_list)

    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_value('HR Settings', None, 'default_grd_supervisor')
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_value('HR Settings', None, 'default_grd_operator')
    def set_new_expiry_date(self):
        if self.category != "Extend":
            self.new_residency_expiry_date = frappe.db.get_value("Employee", self.employee, "work_permit_expiry_date")


    def set_company_address(self):
        """
        This method sets the company address from MOCI document
        """

        missing_field = False
        fields = ['company_pam_file_number','company_location','company_block_number','company_street_name','company_building_name','company_contact_number']
        for field in fields:
            if not self.get(field):
                missing_field = True
        if missing_field:
            moci = frappe.get_doc('MOCI License','ONE Facilities Management Company W.L.L.')
            self.company_location = moci.city
            self.company_block_number = moci.blook
            self.company_street_name = moci.street
            self.company_building_name = moci.building
            self.company_pam_file_number = moci.company_civil_id
        if not self.company_email_id:self.company_email_id=self.company.email
        if not self.company_contact_number:self.company_contact_number=self.company.phone_no


    def set_company_unified_number(self):
        """
        runs: `validate`
        This method to set the unified number from private pam file to moi document
        """
        if not self.company_centralized_number:
            number = frappe.db.get_value('PAM File',{'pam_file_number':self.company_pam_file_number},['company_unified_number'])
            if number:
                self.company_centralized_number = number

    def set_paci_number(self):
        """
        This method sets the paci number in moi document from pam authorized signatury under same file
        """
        if not self.paci_number:
            paci_number = frappe.db.get_value('PAM Authorized Signatory List',{'pam_file_number':self.company_pam_file_number},['company_paci_number'])
            self.paci_number = paci_number

    def set_mendatory_fields(self,field_list):
        mandatory_fields = []
        for fields in field_list:
            for field in fields:
                if not self.get(fields[field]):
                    mandatory_fields.append(field)

        if len(mandatory_fields) > 0:
            message= 'Mandatory fields required in Residency form<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' + mandatory_field +'</li>'
            message += '</ul>'
            frappe.throw(message)

    def get_passport_arabic(self, passport):
        return {'Normal':'طبيعي','Diplomat':'دبلوماسي'}.get(passport)
    

#=================================================================> Reminder Notification
def system_remind_renewal_operator_to_apply():# cron job at 4pm
    """This is a cron method runs every day at 4pm. It gets Draft renewal MOI list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")
    moi_list = frappe.db.get_list('Residency',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['in',('Renewal','Extend')]},
    ['one_fm_civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])
    
    if is_scheduler_emails_enabled():
        notification_reminder(moi_list,supervisor,renewal_operator,"Renewal or Extend")


def system_remind_transfer_operator_to_apply():# cron job at 4pm
    """This is a cron method runs every day at 4pm. It gets Draft transfer MOI list and reminds operator to apply on pam website"""
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
    moi_list = frappe.db.get_list('Residency',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['=',('Transfer')]},
    ['one_fm_civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])
    
    if is_scheduler_emails_enabled():
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
            frappe.db.set_value('Residency',moi.name,'reminded_grd_operator_again',1)
    elif first_reminder_list and len(first_reminder_list)>0:
        email_notification_reminder(operator,first_reminder_list,"First Reminder","Apply for",type)
        for moi in first_reminder_list:
            frappe.db.set_value('Residency',moi.name,'reminded_grd_operator',1)

def email_notification_reminder(grd_user,moi_list,reminder_number, action,type, cc=[]):
    """
    This method send email to the required operator with the list of Residency that their date of application is today or passed already
    """
    message_list=[]
    for moi in moi_list:
        page_link = get_url(frappe.get_doc("Residency", moi.name).get_url())
        message = "<a href='{0}'>{1}</a>".format(page_link, moi.one_fm_civil_id)
        message_list.append(message)

    if message_list:
        message = "<p>{0}: Please {1} {2} Residency</p><ol>".format(reminder_number,action,type)
        for msg in message_list:
            message += "<li>"+msg+"</li>"
        message += "<ol>"
        make(
            subject=_('{0}: {1} {2} Residency'.format(reminder_number,action,type)),
            content=message,
            recipients=[grd_user],
            cc=cc,
            send_email=True,
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
