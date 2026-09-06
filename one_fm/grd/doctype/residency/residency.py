# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
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
from one_fm.utils import is_scheduler_emails_enabled
from one_fm.grd.utils import attach_employee_document

class Residency(Document):
    company = frappe.db.get_value("Company", frappe.defaults.get_global_default('company'), 
            ['phone_no', 'email', 'company_name_arabic'], as_dict=1)
    
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

    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        self.set_residency_expiry_new_date_in_employee_doctype()
        self.apply_damj_civil_id()
        self.db_set('completed_on', now_datetime())
        if self.category == "Transfer":
            self.recall_create_paci()

    def apply_damj_civil_id(self):
        """Put the corrected Civil ID on the Employee once the Damj is completed (WI-002022).

        A Damj merges two civil ID numbers the government issued the same person, and the
        surviving one is the original. Until it is written back, every record that reads
        the Civil ID off the Employee - and every one already holding the superseded
        number - is wrong.

        Written with `db_set`/`set_value` rather than a full Employee save for the same
        reason `set_residency_expiry_new_date_in_employee_doctype` does: a full save
        re-validates the whole Employee, and 1,124 of them hold a Marital Status the
        field's options no longer accept, so any such save throws on data that has
        nothing to do with the civil ID.

        This record's own mirror of the number is updated too. It is fetched from the
        Employee and would otherwise keep showing the number the merge just retired, on
        the very document that recorded the merge.
        """
        if not (self.damj_is_applicable and self.original_civil_id):
            return

        frappe.db.set_value('Employee', self.employee, 'one_fm_civil_id', self.original_civil_id)
        self.db_set('one_fm_civil_id', self.original_civil_id)
        self.sync_damj_civil_id_to_paci()

    def sync_damj_civil_id_to_paci(self):
        """Carry the merged Civil ID over to the PACI opened alongside this Residency (WI-002027).

        The PACI's Civil ID is fetched from the Employee, which means it is copied once at
        insert and never looked at again. A Damj completed after the PACI was opened
        therefore leaves the civil ID application quoting the number the government just
        retired - the one thing it must not do.

        Scoped to the same Preparation, which is what pairs the two documents: a
        Preparation opens one Residency and one PACI per employee, so that pair is the
        "linked record" the story means. A Residency with no Preparation - a transfer, say
        - has no PACI to pair with and is left alone.

        Cancelled records are skipped; there can be more than one live PACI for the same
        employee (a rejected application and its replacement), and both need the
        correction. Written with set_value because the field is read-only and the PACI may
        already be submitted, and because a full save would re-run the PACI's own
        validation over a document this change has no business re-validating.
        """
        if not self.preparation:
            return

        for paci_name in frappe.get_all(
            'PACI',
            filters={
                'preparation': self.preparation,
                'employee': self.employee,
                'docstatus': ['!=', 2],
            },
            pluck='name',
        ):
            frappe.db.set_value('PACI', paci_name, 'civil_id', self.original_civil_id)

    def recall_create_paci(self):
        paci.create_PACI_for_transfer(self.employee)

    def validate_mandatory_fields_on_submit(self):
        field_list = [{'Upload Payment Invoice':'invoice_attachment'},{'Updated Residency Expiry Date':'new_residency_expiry_date'}]
        self.set_mendatory_fields(field_list)

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

    def set_residency_expiry_new_date_in_employee_doctype(self):
        """
        runs: `on_submit`
        Record the new residency attachment and expiry date on the Employee.

        The two facts are written directly rather than through a full save of the
        Employee, which re-validates every field on it - so completing a Residency
        failed on data that has nothing to do with it: 1,124 employees hold a Marital
        Status the field's options no longer accept ("Single", "Divorced", "Widowed").

        The old version rebuilt the whole child table to keep it ordered, and inserted
        the new row beside the existing one rather than over it, so every renewal left
        another Residency Expiry Attachment behind. The helper updates the row in place.
        """
        attach_employee_document(
            self.employee,
            document_name="Residency Expiry Attachment",
            attach=self.residency_attachment,
            valid_till=self.new_residency_expiry_date,
            issued_on=date.today(),
        )
        frappe.db.set_value(
            "Employee", self.employee, "residency_expiry_date", self.new_residency_expiry_date
        )

    def get_passport_arabic(self, passport):
        return {'Normal':'طبيعي','Diplomat':'دبلوماسي'}.get(passport)
    

# The Actions whose Residency is opened by Preparation's own dispatcher rather than by
# the "for extend" branch below (WI-001824). Without this the branch - which reads as
# "anything that is not a renewal is an extension" - would open a second Residency for
# them, categorised as Extend.
ACTIONS_HANDLED_ON_SUBMIT = (
    'Renewal Expat', 'New Kuwaiti', 'Overseas', 'Overseas (Government)', 'Local Transfer'
)

# The Residency a category opens, and how many days before the residency expires it is
# applied for. Anything not listed is an extension, applied for a week ahead.
MOI_CATEGORY_BY_ACTION = {
    'Renewal Expat': ('Renewal', -14),
    'Transfer': ('Transfer', None),
    # Same category whether the transfer came from a Transfer Paper (which says
    # "Transfer") or from a Preparation row (which says "Local Transfer").
    'Local Transfer': ('Transfer', None),
    # First residency for an overseas hire (WI-001881): there is no expiry to count
    # back from, so it is applied for the day the Preparation was submitted.
    'Overseas': ('First Time', None),
    # WI-002024: a government-contract overseas hire gets the same first residency. MOI
    # does not care which file the work permit was raised against.
    'Overseas (Government)': ('First Time', None),
}


#fetching the list of employee has Extend and renewal status from HR list.
def set_employee_list_for_moi(preparation_name):
    # filter work permit records only take the non kuwaiti
    employee_in_preparation = frappe.get_doc('Preparation',preparation_name)
    if employee_in_preparation.preparation_record:
        for employee in employee_in_preparation.preparation_record:
            if employee.renewal_or_extend == 'Renewal Expat' and employee.nationality != 'Kuwaiti':# For renewals
                try:
                    create_moi_record(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)
                except Exception as e:
                    frappe.log_error(message=frappe.get_traceback(), title=f"Error creating MOI for Employee {employee.employee} in Preparation {preparation_name}")
                    continue
            if (
                employee.renewal_or_extend not in ACTIONS_HANDLED_ON_SUBMIT
                and employee.nationality != 'Kuwaiti'
            ):# For extend
                try:
                    create_moi_record(frappe.get_doc('Employee',employee.employee),employee.renewal_or_extend,preparation_name)
                except Exception as e:
                    frappe.log_error(message=frappe.get_traceback(), title=f"Error creating MOI for Employee {employee.employee} in Preparation {preparation_name}")
                    continue

# Open the MOI for a transferred employee, called when their Medical Insurance is
# marked Done. Named "creat_moi_for_transfer" until the module was renamed from
# moi_residency_jawazat to residency: that refactor corrected the spelling at the call
# site but not here, so every Local Transfer insurance raised AttributeError on submit
# and the MOI was never opened.
def create_moi_for_transfer(work_permit_name):
    work_permit = frappe.get_doc('Work Permit',work_permit_name)
    if work_permit:
        employee = frappe.get_doc('Employee',work_permit.employee)
        if employee:
            # The employee is already loaded; re-fetching it through its own mirror
            # field only risked a second lookup failing.
            create_moi_record(employee,"Transfer")

def create_moi_record(employee,Renewal_or_Extend,preparation_name = None, category=None):
    """Open the Residency an Action calls for.

    WI-002033: a Preparation row states the category in NEW_ACTION_DOCUMENTS and passes it
    in, so the table an operator reads to see what an Action produces is the one the
    document is actually opened under. The map below still supplies the application date -
    how many days before the residency expires it is applied for - which the caller does
    not know, and still supplies the category for the callers that pass none: the transfer
    path and the extend branch.
    """
    mapped_category, days_before_expiry = MOI_CATEGORY_BY_ACTION.get(
        Renewal_or_Extend, ("Extend", -7)
    )
    category = category or mapped_category
    start_date = add_days(employee.residency_expiry_date, days_before_expiry) if days_before_expiry else today()


    # start_day_for_renewal = add_days(employee.residency_expiry_date, -14)# MIGHT CHANGE IN TRANSFER
    new_moi = frappe.new_doc('Residency')
    new_moi.employee = employee.name
    new_moi.preparation = preparation_name
    new_moi.renewal_or_extend = Renewal_or_Extend
    new_moi.date_of_application = start_date
    new_moi.category = category
    new_moi.insert()

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
