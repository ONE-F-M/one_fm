# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from one_fm.api.notification import create_notification_log
from frappe.utils import today, add_days, get_url, date_diff, get_year_start, flt
from frappe.utils import get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr
from frappe.core.doctype.communication.email import make
from one_fm.processor import sendemail
from one_fm.grd.document_title import set_document_title
from one_fm.utils import is_scheduler_emails_enabled
from one_fm.grd.processa import cancel_processes




class PACI(Document):
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
            cancel_processes(self.doctype, existing_docs, _("Replaced by a newer PACI"))
            frappe.db.commit()


    def validate(self):
        self.set_grd_values()
        set_document_title(self)
        self.set_new_expiry_date()
        self.set_paci_fine_amount()
        self.clear_unticked_damj_details()
        self.validate_exception_details()

    def validate_exception_details(self):
        """Hold the save until a ticked exception carries its evidence (WI-002109).

        mandatory_depends_on is a form rule only - Frappe's server-side mandatory check reads
        `reqd` and nothing else - so a record arriving by import or through the API would
        otherwise claim a Damj merge with no original civil ID and no letter behind it.

        A fine amount of zero counts as missing: the amount comes from the master rate in HR
        Settings, so a ticked box that produces nothing means the rate is not configured, and
        a zero-value fine has nothing for finance to reference. Same rule Residency applies.
        """
        field_list = []

        if self.damj_is_applicable:
            field_list += [
                {'Original Civil ID': 'original_civil_id'},
                {'Upload DAMJ Letter': 'upload_damj_letter'},
            ]

        if field_list:
            self.set_mendatory_fields(field_list)

        # The fine amount is read-only and comes from the master rate, so a ticked box that
        # produces nothing is a gap in HR Settings rather than something the operator forgot
        # to type - and the message has to say so, or it points at a field they cannot edit.
        # WI-002109 requires the amount to be greater than zero; WI-002023 let a record save
        # with a zero fine, which recorded a fine finance had nothing to reference.
        if self.is_paci_fine_applicable and not flt(self.paci_fine_amount_kwd):
            frappe.throw(
                _("The PACI fine rate is not configured. Set <b>PACI Fine Amount (KWD)</b> in "
                  "HR Settings, or untick <b>Is PACI Fine Applicable?</b>."),
                title=_("PACI Fine Rate Not Configured"),
            )

    def clear_unticked_damj_details(self):
        """Empty the Damj details when the box is unticked (WI-002109).

        Both fields are hidden then, so anything left in them is invisible - and an original
        civil ID still on a record that no longer claims a merge is the number the employee's
        profile would be set to if the box were ever ticked again.

        Cleared on the server rather than only in the browser: the box can be unticked by an
        import, a patch or the API, none of which run the form's handlers. The fine amount
        already clears itself the same way in set_paci_fine_amount.
        """
        if self.damj_is_applicable:
            return

        self.original_civil_id = None
        self.upload_damj_letter = None
        self.upload_damj_letter_on = None

    def set_paci_fine_amount(self):
        """Fetch the PACI late fine off HR Settings, or clear it (WI-002023).

        The rate is fixed by PACI, not negotiated per record, so the operator states
        whether the fine applies and the amount follows from the master rate. Derived on
        every save rather than only when the box is ticked, so a record saved after PACI
        changes the rate carries the rate that was current when it was saved, and the
        field cannot be left holding a number the operator typed by hand.

        Cleared to 0 when the box is unticked. The field is hidden then, so a stale amount
        left behind would be invisible and still reach the costing.
        """
        if not self.is_paci_fine_applicable:
            self.paci_fine_amount_kwd = 0
            return

        self.paci_fine_amount_kwd = flt(
            frappe.db.get_single_value('HR Settings', 'paci_fine_amount_kwd')
        )


    def set_grd_values(self):
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_value('HR Settings', None, 'default_grd_supervisor')
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_value('HR Settings', None, 'default_grd_operator')
        if not self.grd_operator_transfer:
            self.grd_operator_transfer = frappe.db.get_value('HR Settings', None, 'default_grd_operator_transfer')

    def set_new_expiry_date(self):
        """
        Set civil ID and residency expiry dates from employee's work permit expiry date.
        
        - For new documents: Sets new_civil_id_expiry_date.
        - When payment invoice is uploaded: Sets both new_civil_id_expiry_date and residency_expiry_date.
        """
        payment_invoice_uploaded = (self.has_value_changed('upload_civil_id_payment') and self.upload_civil_id_payment)
        if self.is_new() or payment_invoice_uploaded:
            work_permit_expiry = frappe.db.get_value("Employee", self.employee, "work_permit_expiry_date")
            self.new_civil_id_expiry_date = work_permit_expiry
            if payment_invoice_uploaded:
                self.residency_expiry_date = work_permit_expiry


    def on_update(self):
        # The PACI Lifecycle process checks the PRO submission and the payment invoice in
        # its script tasks before it moves the record on.
        self.stamp_damj_letter()

    def stamp_damj_letter(self):
        """Record when the Damj letter went up, from the server's clock (WI-002109).

        The Attach field is allow_on_submit, so the letter can arrive after the record is
        submitted - which is why this is on on_update and written with db_set.
        """
        if self.upload_damj_letter and not self.upload_damj_letter_on:
            self.db_set("upload_damj_letter_on", now_datetime())
        elif not self.upload_damj_letter and self.upload_damj_letter_on:
            self.db_set("upload_damj_letter_on", None)

    def set_mendatory_fields(self,field_list):
        mandatory_fields = []
        for fields in field_list:
            for field in fields:
                if not self.get(fields[field]):
                    mandatory_fields.append(field)

        if len(mandatory_fields) > 0:
            message= 'Mandatory fields required in PACI form<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' + mandatory_field +'</li>'
            message += '</ul>'
            frappe.throw(message)

def create_PACI(employee,Type,preparation_name = None):
        # Create New PACI: 1. New Overseas, 2. New Kuwaiti, 3. Transfer
        if Type == "Renewal":
            start_day = add_days(employee.residency_expiry_date, -14)# MIGHT CHANGE
        else:
            # Every other category - Transfer, and New Application for an overseas hire
            # (WI-001881) - has no residency expiry to count back from, so the civil ID is
            # applied for the day the record is opened.
            start_day = today()
        PACI_new = frappe.new_doc('PACI')
        PACI_new.employee = employee.name
        PACI_new.category = Type
        PACI_new.preparation = preparation_name
        PACI_new.date_of_application = start_day
        # The PACI Lifecycle process hands a New Application straight to the PRO.
        PACI_new.save()
        return PACI_new


#==============================================================================> Reminder Notification
def notify_operator_to_take_hawiyati_renewal():# cron job at 8am in working days
    renewal_list=[]
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")
    paci_list_renewal = frappe.db.get_list('PACI',{'category':'Renewal','workflow_state':"Under Process",'upload_hawiyati':['=','']},['civil_id','name','payment_date'])
    for paci in paci_list_renewal:
        if date_diff(date.today(),getdate(paci.payment_date))>=2:
            renewal_list.append(paci)

    if is_scheduler_emails_enabled():
        email_notification_reminder(renewal_operator,paci_list_renewal,"Reminder","Upload Hawiyati for","Renewal", supervisor)

def notify_operator_to_take_hawiyati_transfer(): # cron job at 8am in working days
    transfer_list=[]
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
    paci_list_transfer = frappe.db.get_list('PACI',{'category':'Transfer','workflow_state':"Under Process",'upload_hawiyati':['=','']},['civil_id','name','payment_date'])
    for paci in paci_list_transfer:
        if date_diff(date.today(),getdate(paci.payment_date))>=2:
            transfer_list.append(paci)

    if is_scheduler_emails_enabled():
        email_notification_reminder(transfer_operator,paci_list_transfer,"Reminder","Upload Hawiyati for","Transfer", supervisor)

def system_remind_renewal_operator_to_apply():# cron job at 8am in working days
    """
    This is a cron method runs every day at 8am. It gets Draft renewal PACI list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")
    paci_list = frappe.db.get_list('PACI',
    {'date_of_application':['<=',date.today()],'workflow_state':['=',('Apply Online by PRO')],'category':['=',('Renewal')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])

    if is_scheduler_emails_enabled():
        notification_reminder(paci_list,supervisor,renewal_operator,"Renewal")


def system_remind_transfer_operator_to_apply():# cron job at 8am in working days
    """
    This is a cron method runs every day at 8am. It gets Draft transfer PACI list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
    paci_list = frappe.db.get_list('PACI',
    {'date_of_application':['<=',today()],'workflow_state':['=',('Apply Online by PRO')],'category':['=',('Transfer')]},['civil_id','name','reminder_grd_operator','reminder_grd_operator_again'])

    if is_scheduler_emails_enabled():
        notification_reminder(paci_list,supervisor,transfer_operator,"Transfer")


def notification_reminder(paci_list,supervisor,operator,type):
    """
    This method sends first, second, reminders and then send third one and cc supervisor in the email
    """
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
    """
    This method send email to the required operator with the list of PACI that their date of application is today or passed already
    """
    message_list=[]
    for paci in paci_list:
        page_link = get_url(frappe.get_doc("PACI", paci.name).get_url())
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

def send_email(doc, recipients, message, subject):
	sendemail(
		recipients= recipients,
		subject=subject,
		message=message,
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)


# ── Reapplying after a PACI rejection (WI-001830 AC4) ─────────────────────────
#
# Cleared on the new application: the reference the rejected attempt was given and the
# reason it was refused. Everything else - the candidate, the category, the Preparation
# that started it - comes across, which is the point of the button.
REJECTED = "Rejected"
REJECTION_OUTCOME_FIELDS = (
    "paci_reference_number",
    "paci_rejection_reason",
    "upload_civil_id_payment",
    "payment_date",
    "payment_made_via",
    "bank_account",
    "upload_civil_id",
    "upload_civil_id_datetime",
    "upload_hawiyati",
    "completed_on",
)


def can_reapply(doc) -> bool:
    """Is this an application a fresh attempt can be raised from (WI-001830)?

    The gate the button and the server share, so the button cannot offer something the
    method then refuses.
    """
    return doc.get("workflow_state") == REJECTED


@frappe.whitelist(methods=["POST"])
def reapply_paci(name: str):
    """Raise a fresh PACI from one that was rejected (WI-001830 AC4).

    A copy rather than a new document with a few fields set: the candidate's details are
    what the AC asks to keep, and re-entering them is what the button exists to avoid.
    The rejected application is left as the audit history, and ``rejected_paci`` on the
    new one is the parent reference link back to it.
    """
    source = frappe.get_doc("PACI", name)
    source.check_permission("read")

    if not frappe.has_permission("PACI", "create"):
        frappe.throw(_("You do not have permission to create a PACI."), frappe.PermissionError)

    if not can_reapply(source):
        frappe.throw(
            _("Only a PACI in <b>{0}</b> can be reapplied. {1} is in {2}.").format(
                REJECTED, source.name, source.workflow_state
            ),
            title=_("Cannot Reapply"),
        )

    reapplication = frappe.copy_doc(source)
    for fieldname in REJECTION_OUTCOME_FIELDS:
        reapplication.set(fieldname, None)

    reapplication.workflow_state = "Draft"
    reapplication.date_of_application = today()
    reapplication.rejected_paci = source.name
    reapplication.insert()

    return {"name": reapplication.name}
