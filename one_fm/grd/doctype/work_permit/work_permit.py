# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url, date_diff
from frappe import _
from one_fm.api.notification import create_notification_log
from frappe.permissions import has_permission
from frappe.utils.user import get_users_with_role
from datetime import date, timedelta
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, get_datetime, add_to_date, getdate, get_link_to_form, now_datetime, nowdate, cstr, get_url_to_form
from email import policy
from one_fm.grd.doctype.fingerprint_appointment import fingerprint_appointment
from one_fm.grd.doctype.medical_insurance import medical_insurance
from frappe.core.doctype.communication.email import make
from one_fm.processor import sendemail
from one_fm.grd.document_title import set_document_title
from one_fm.utils import send_workflow_action_email, is_scheduler_emails_enabled
from one_fm.grd.processa import cancel_processes

# from PyPDF2 import PdfFileReader

# from pdfminer.pdfparser import PDFParser, PDFDocument
class WorkPermit(Document):
    def onload(self):
        if self.docstatus == 0:
            self.employee_last_checkin = get_employee_last_checkin(self.employee)

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
            cancel_processes(self.doctype, existing_docs, _("Replaced by a newer Work Permit"))
            frappe.db.commit()

    def validate(self):
        self.set_grd_values()
        set_document_title(self)
        self.employee_last_checkin = get_employee_last_checkin(self.employee)

        if self.employee:
            employee_details = frappe.db.get_value("Employee", self.employee, ["status", "relieving_date", "employee_name"], as_dict=True)
            if employee_details.status != "Active":
                frappe.throw(_("{0}'s status is currently not active. Work Permit processing is only allowed for active employees").format(employee_details.employee_name))
            if employee_details.relieving_date:
                frappe.throw(_("{0}'s Relieving Date has been set to {1}. Work Permit processing is not allowed.").format(employee_details.employee_name, employee_details.relieving_date))

    def set_grd_values(self):
        """
		runs: `validate`
		param: work permit object
		This method is fetching values of grd supervisor and operator for transfer, pifss operator from HR Settings
		"""
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")
        if not self.grd_operator_transfer:
            self.grd_operator_transfer = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
        if not self.pam_operator:
            self.pam_operator = pam_operator_email = frappe.db.get_single_value("HR Settings", 'default_pam_operator')

    def validate_mandatory_fields_for_grd_operator_again(self):
        users = frappe.utils.user.get_users_with_role('Government Relations Operator')
        filtered_users = []
        for user in users:
            if has_permission(doctype=self.doctype, user=user):
                filtered_users.append(user)
            if filtered_users and len(filtered_users) > 0:
                if (
                    "Pending By PAM Operator" in self.workflow_state
                    and not self.attach_invoice
                    and self.invoice_required()
                ):
                    frappe.throw(_("Upload Required Documents To Submit"))

    def notify_grd(self,message,subject,user):
        if user == "Government Relations Operator":
            send_email(self, [self.grd_operator], message, subject)
            create_notification_log(subject, message, [self.grd_operator], self)
        if user == "GRD Supervisor":
            send_email(self, [self.grd_supervisor], message, subject)
            create_notification_log(subject, message, [self.grd_supervisor], self)

    def clean_old_wp_record_in_employee_doctype(self):
        """ Clean old wp records in employee """
        to_remove = []
        employee = frappe.get_doc('Employee', self.employee)
        if employee.one_fm_employee_documents:
            for document in employee.one_fm_employee_documents:
                if document.document_name == "Work Permit":
                    to_remove.append(document)
            [document.delete(document) for document in to_remove]

    @frappe.whitelist()
    def get_required_documents(self):
        set_required_documents(self)

    def get_under_company_residency_on_completion(self):
        """The Employee's under_company_residency once this permit is Completed.

        1 for a completed permit that puts the employee under company residency, 0 for a
        completed Cancellation, None when the permit must not touch the flag (Kuwaitis are
        not under company residency, and a permit that is not Completed changes nothing).
        """
        if self.workflow_state != "Completed":
            return None
        if self.work_permit_type == "Cancellation":
            return 0
        if self.work_permit_type in ("Renewal Kuwaiti", "New Kuwaiti"):
            return None
        return 1

    def on_cancel(self):
        self.revert_under_company_residency()

    def revert_under_company_residency(self):
        """Cancelling a Completed permit undoes what its completion did to the flag.

        workflow_state stays Completed on cancel, so the same rule tells which way it went.
        The save recomputes the residency digit of employee_id.
        """
        residency = self.get_under_company_residency_on_completion()
        if residency is None:
            return
        employee = frappe.get_doc("Employee", self.employee)
        restored = 1 - residency
        if cint(employee.under_company_residency) != restored:
            employee.under_company_residency = restored
            employee.save()

def set_required_documents(doc):
    if frappe.db.exists('Work Permit Required Documents Template', {'work_permit_type':doc.work_permit_type}):
        #getting the required documents template based on the wp type
        document_list_template = frappe.get_doc('Work Permit Required Documents Template', {'work_permit_type':doc.work_permit_type})
        employee = frappe.get_doc('Employee', doc.employee)#getting employee info.
        if document_list_template and document_list_template.work_permit_document:
            for wpd in document_list_template.work_permit_document:
                documents_required = doc.append('documents_required')#in work permit doctype points to Work Permit Required Documents
                documents_required.required_document = wpd.required_document
                if employee.one_fm_employee_documents:# from employee dt
                    for ed in employee.one_fm_employee_documents:
                        if wpd.required_document == ed.document_name and ed.attach:#check if both documents are equal
                            documents_required.attach = ed.attach#add the attach document from (Employee Document)dt to (Work permit Required Document) attch field
            frappe.db.commit()

# Create Work Permit Record for new Kuwaiti
def create_work_permit_new_kuwaiti(pifss_name,employee):
    pifss103_form = frappe.get_doc('PIFSS Form 103',pifss_name)
    if pifss103_form:
        employee_in_pifss103_form = frappe.get_doc('Employee',employee)
        if employee_in_pifss103_form:
            create_wp_kuwaiti(frappe.get_doc('Employee',employee_in_pifss103_form.employee),"New Kuwaiti",pifss_name)

# Create Work Permit Record for Transfer
@frappe.whitelist()
def create_work_permit_transfer(tp_name,employee):
    tp = frappe.get_doc('Transfer Paper',tp_name)
    if tp:
        employee_in_tp = frappe.get_doc('Employee',employee)
        if employee_in_tp:
            create_wp_transfer(frappe.get_doc('Employee',employee_in_tp.employee),"Local Transfer",tp_name)#check if you need to do it this way create_wp_transfer(employee_in_tp,"Local Transfer",tp_name)


def create_wp_from_preparation(employee, work_permit_type, preparation_name):
    """Open a Work Permit for a Preparation row whose Action is not a renewal (WI-001824).

    A renewal dates its application off the residency it is renewing, which is what
    create_wp_renewal does. A New Kuwaiti or Overseas application has no residency yet,
    so it is applied for on the day the Preparation is submitted.

    No copy of a previous Work Permit either: these are first applications, so there is
    nothing to carry forward, and copying one would bring the old PAM references with it.
    """
    work_permit = frappe.new_doc('Work Permit')
    work_permit.employee = employee.name
    work_permit.work_permit_type = work_permit_type
    work_permit.date_of_application = today()
    work_permit.preparation = preparation_name
    work_permit.ref_doctype = 'Preparation'
    work_permit.ref_name = preparation_name
    work_permit.insert()

    return work_permit


#FOR RENEWAL
def create_work_permit_renewal(preparation_name):
    """Open a renewal Work Permit for every row the Action calls for.

    Returns the rows it could not open one for, so the submitting operator is told
    rather than left reading a clean submit: the Error Log entry alone is invisible to
    them, and a missing permit silently costs the employee their Medical Insurance too.
    """
def create_wp_renewal(employee,status,name):
    if status and status in ['Renewal Expat',"Renewal (Kuwaiti)"]:
        start_day = add_days(employee.residency_expiry_date, -14)
        Doctype = "Preparation"
        preparation_name = name
    # setting type of renewal work permit
        if employee.one_fm_nationality == "Kuwaiti":
            work_permit_type = "Renewal Kuwaiti"
        if employee.one_fm_nationality != "Kuwaiti":
            work_permit_type = "Renewal Expat"

    if employee.work_permit:
        work_permit = frappe.get_doc('Work Permit', employee.work_permit)
        new_work_permit = frappe.copy_doc(work_permit)
        new_work_permit.employee = employee.name
        new_work_permit.preparation = preparation_name
        new_work_permit.work_permit_type = work_permit_type
        new_work_permit.date_of_application = start_day
        new_work_permit.transfer_paper = None
        new_work_permit.ref_doctype = Doctype
        new_work_permit.ref_name = name
        new_work_permit.insert()
    else:
        work_permit = frappe.new_doc('Work Permit')
        work_permit.employee = employee.name
        work_permit.preparation = preparation_name
        work_permit.work_permit_type = work_permit_type
        work_permit.date_of_application = start_day
        work_permit.ref_doctype = Doctype
        work_permit.ref_name = name
        work_permit.transfer_paper = None
        work_permit.save()

#FOR Transfer
def create_wp_transfer(employee,status,name):
    if status == "Local Transfer":
            start_day = today()
            Doctype = "Transfer Paper"
            work_permit_type = "Local Transfer"
            preparation_name = None
    if employee.work_permit:
        work_permit = frappe.get_doc('Work Permit', employee.work_permit)
        new_work_permit = frappe.copy_doc(work_permit)
        new_work_permit.employee = employee.name
        new_work_permit.preparation = None
        new_work_permit.work_permit_type = work_permit_type
        new_work_permit.date_of_application = start_day
        new_work_permit.ref_doctype = Doctype
        new_work_permit.ref_name = name
        new_work_permit.transfer_paper = name
        new_work_permit.insert()
    else:
        work_permit = frappe.new_doc('Work Permit')
        work_permit.employee = employee.name
        work_permit.preparation = None
        work_permit.work_permit_type = work_permit_type
        work_permit.date_of_application = start_day
        work_permit.ref_doctype = Doctype
        work_permit.ref_name = name
        work_permit.transfer_paper = name
        work_permit.save()


#For New Kuwaiti New Kuwaiti
def create_wp_kuwaiti(employee,status,name):
    if status == "New Kuwaiti":
        start_day = today()
        Doctype = "PIFSS Form 103"
        work_permit_type = "New Kuwaiti"
    if employee.work_permit:
        work_permit = frappe.get_doc('Work Permit', employee.work_permit)
        new_work_permit = frappe.copy_doc(work_permit)
        new_work_permit.employee = employee.name
        new_work_permit.preparation = None
        new_work_permit.work_permit_type = work_permit_type
        new_work_permit.date_of_application = start_day
        new_work_permit.ref_doctype = Doctype
        new_work_permit.ref_name = name
        new_work_permit.transfer_paper = None
        new_work_permit.insert()
    else:
        work_permit = frappe.new_doc('Work Permit')
        work_permit.employee = employee.name
        work_permit.preparation = None
        work_permit.work_permit_type = work_permit_type
        work_permit.date_of_application = start_day
        work_permit.ref_doctype = Doctype
        work_permit.ref_name = name
        work_permit.transfer_paper = None
        work_permit.save()

#===================================================> Reminder Notification
def system_remind_renewal_operator_to_apply():
    """
    This is a cron method runs every day at 8am. It gets Draft `renewal` work permit list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    renewal_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")
    work_permit_list = frappe.db.get_list('Work Permit',
    {'date_of_application':['<=',today()],'workflow_state':['in',('Draft','Apply Online by PRO')],'work_permit_type':['in',('Renewal Expat','Renewal Kuwaiti')]},['civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])

    if is_scheduler_emails_enabled():
        notification_reminder(work_permit_list,supervisor,renewal_operator,"Renewal")

def system_remind_transfer_operator_to_apply():
    """
    This is a cron method runs every day at 8am. It gets Draft `transfer` work permit list and reminds operator to apply on pam website
    """
    supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
    transfer_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator_transfer")
    work_permit_list = frappe.db.get_list('Work Permit',
    {'date_of_application':['<=',today()],'workflow_state':['in',('Draft','Apply Online by PRO')],'work_permit_type':['=',('Local Transfer')]},['civil_id','name','reminded_grd_operator','reminded_grd_operator_again'])

    if is_scheduler_emails_enabled():
        notification_reminder(work_permit_list,supervisor,transfer_operator,"Local Transfer")


def notification_reminder(work_permit_list,supervisor,operator,type):
    """
    This method sends first, second, reminders and then send third one and cc supervisor in the email
    """
    first_reminder_list=[]
    second_reminder_list=[]
    penality_reminder_list=[]
    if work_permit_list and len(work_permit_list) > 0:
        for wp in work_permit_list:
            if wp.reminded_grd_operator_again:
                penality_reminder_list.append(wp)
            elif wp.reminded_grd_operator and not wp.reminded_grd_operator_again:
                second_reminder_list.append(wp)
            elif not wp.reminded_grd_operator:
                first_reminder_list.append(wp)

    if penality_reminder_list and len(penality_reminder_list)>0:
        email_notification_reminder(operator,penality_reminder_list,"Third Reminder","Apply for",type,supervisor)
    elif second_reminder_list and len(second_reminder_list)>0:
        email_notification_reminder(operator,second_reminder_list,"Second Reminder","Apply for",type)
        for wp in second_reminder_list:
            frappe.db.set_value('Work Permit',wp.name,'reminded_grd_operator_again',1)
    elif first_reminder_list and len(first_reminder_list)>0:
        email_notification_reminder(operator,first_reminder_list,"First Reminder","Apply for",type)
        for wp in first_reminder_list:
            frappe.db.set_value('Work Permit',wp.name,'reminded_grd_operator',1)

def email_notification_reminder(grd_user,work_permit_list,reminder_number, action,type, cc=[]):
    """
    This method send email to the required operator with the list of work permit that their date of application is today or passed already
    """
    message_list=[]
    for work_permit in work_permit_list:
        page_link = get_url(frappe.get_doc("Work Permit", work_permit.name).get_url())
        message = "<a href='{0}'>{1}</a>".format(page_link, work_permit.civil_id)
        message_list.append(message)

    if message_list:
        message = "<p>{0}: Please {1} {2} Work Permit listed below</p><ol>".format(reminder_number,action,type)
        for msg in message_list:
            message += "<li>"+msg+"</li>"
        message += "<ol>"
        make(
            subject=_('{0}: {1} {2} Work Permit'.format(reminder_number,action,type)),
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

@frappe.whitelist()
def get_employee_last_checkin(employee):
    """
        Return last_checkin_date (MAX(date) in Employee Checkin) for each employee.
    """
    if not employee:
        return {}
    result = frappe.db.sql(
        """
        SELECT
            MAX(date) AS last_checkin_date
        FROM `tabEmployee Checkin` e
        WHERE e.employee = %(employee)s
        """,
        {"employee": employee},
        as_dict=True,
    )
    if len(result) > 0:
        return result[0].last_checkin_date
    return None

# ── Previous company response window (WI-001829) ──────────────────────────────
#
# PAM gives the previous employer three working days to answer a Local Transfer.
# Silence past that is a refusal, and it is recorded under its own reason so a report can
# tell it apart from an employer who actually said no.
PREVIOUS_COMPANY_STATE = "Pending By Previous Company"
PREVIOUS_COMPANY_RESPONSE_DAYS = 3
AUTO_REJECTION_REASON = "Auto rejected after 3 days"
REJECTED_BY_PREVIOUS_COMPANY = "Rejected by previous company"


def auto_reject_unanswered_previous_company():
	"""Reject Local Transfers the previous employer never answered.

	Cron, on the same working-days schedule as the other GRD reminders. Takes the Reject
	action on the Pending By Previous Company task of the Work Permit Lifecycle process,
	which submits the permit as Rejected.
	"""
	from one_fm.grd.processa import complete_action

	waiting = frappe.get_all(
		"Work Permit",
		filters={
			"workflow_state": PREVIOUS_COMPANY_STATE,
			"work_permit_type": "Local Transfer",
			"docstatus": 0,
		},
		fields=["name", "inform_previous_company_on", "modified"],
	)

	for permit in waiting:
		# The clock starts when the previous company was informed. Older permits predate
		# that field, so the last change - which is when it entered this state - stands in.
		informed_on = permit.inform_previous_company_on or permit.modified
		if working_days_between(informed_on, today()) < PREVIOUS_COMPANY_RESPONSE_DAYS:
			continue

		try:
			doc = frappe.get_doc("Work Permit", permit.name)
			doc.db_set(
				{
					"previous_company_rejection_reason": AUTO_REJECTION_REASON,
					"reason_of_rejection": REJECTED_BY_PREVIOUS_COMPANY,
				},
				update_modified=False,
			)
			if not complete_action(doc, "Reject"):
				frappe.throw(_("Work Permit {0} has no open Processa task to reject.").format(doc.name))
		except Exception:
			# One permit that will not transition must not stop the rest of the sweep.
			frappe.log_error(
				title="WI-001829: auto-rejection failed",
				message=f"{permit.name}\n{frappe.get_traceback()}",
			)


# Kuwait's government weekend. Held here rather than read from a Holiday List because
# this window is PAM's, not an employee's - and because the list cannot be relied on for
# it: the company default on production is "Default Company Holiday List 2024", which
# ends in 2024 and carries no weekly off at all, so every Friday since would have counted
# as a working day (WI-001829).
WEEKEND_WEEKDAYS = (4, 5)  # Friday, Saturday


def working_days_between(from_date, to_date):
	"""Working days after `from_date` up to and including `to_date`.

	The weekend is the floor; public holidays come off the company's holiday list on top
	of it, when that list actually covers the dates being counted. So a request that goes
	out on a Wednesday is not three working days old by Saturday.
	"""
	from frappe.utils import getdate

	start, end = getdate(from_date), getdate(to_date)
	if start >= end:
		return 0

	holidays = get_company_holidays(start, end)

	days = 0
	current = add_days(start, 1)
	while current <= end:
		if current.weekday() not in WEEKEND_WEEKDAYS and current not in holidays:
			days += 1
		current = add_days(current, 1)

	return days


def get_company_holidays(from_date, to_date):
	"""Public holidays in a range, from the default company's holiday list.

	An empty set when the list is missing or does not reach these dates - the weekend
	floor in working_days_between is what keeps the count honest in that case.
	"""
	holiday_list = frappe.db.get_value(
		"Company", frappe.defaults.get_global_default("company"), "default_holiday_list"
	)
	if not holiday_list:
		return set()

	return set(
		frappe.get_all(
			"Holiday",
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [from_date, to_date]],
			},
			pluck="holiday_date",
		)
	)


# ── Reapplying after a rejection (WI-001828) ──────────────────────────────────
#
# Cleared on the new attempt: the references PAM issued for the application that was
# refused, and the outcome of that refusal. Everything else - the candidate's details,
# their salary, the contract, the Preparation that started it - is carried over, which is
# the point of the button.
REJECTION_OUTCOME_FIELDS = (
	"reference_number_on_pam_registration",
	"reference_number_registration_set_on",
	"reference_number_on_pam",
	"reference_number_set_on",
	"reason_of_rejection",
	"details_of_rejection",
	"pam_rejection_reason",
	"previous_company_rejection_reason",
	"previous_company_status",
	"inform_previous_company_on",
	"attach_invoice",
	"payment_date",
	"payment_made_via",
	"bank_account",
	"attach_payment_invoice",
	"work_permit_approved",
	"new_work_permit_expiry_date",
)

REJECTED_STATE = "Rejected"


def can_reapply(doc) -> bool:
	"""Is this a permit a fresh attempt can be raised from (WI-001828)?

	The gate the button and the server share, so the button cannot offer something the
	method then refuses.
	"""
	return doc.get("workflow_state") == REJECTED_STATE


@frappe.whitelist(methods=["POST"])
def reapply_work_permit(name: str):
	"""Raise a fresh Work Permit from one that was rejected (WI-001828).

	A copy rather than a new document with a few fields set: the candidate's personal,
	salary and contract details are exactly what the AC asks to keep, and re-entering
	them is what the button exists to avoid.

	The rejected permit is left as it is - it is the audit history, and
	rejected_work_permit on the new one is the link back to it.
	"""
	source = frappe.get_doc("Work Permit", name)
	source.check_permission("read")

	if not frappe.has_permission("Work Permit", "create"):
		frappe.throw(
			_("You do not have permission to create a Work Permit."), frappe.PermissionError
		)

	if not can_reapply(source):
		frappe.throw(
			_("Only a permit in <b>{0}</b> can be reapplied. {1} is in {2}.").format(
				REJECTED_STATE, source.name, source.workflow_state
			),
			title=_("Cannot Reapply"),
		)

	reapplication = frappe.copy_doc(source)
	for fieldname in REJECTION_OUTCOME_FIELDS:
		reapplication.set(fieldname, None)

	reapplication.workflow_state = "Draft"
	reapplication.date_of_application = today()
	reapplication.rejected_work_permit = source.name
	# A fresh application has not been amended: copy_doc ignores no_copy by default, so
	# the count has to be reset here or the new permit inherits the old one's (WI-002108).
	reapplication.amendment_no = 0
	reapplication.insert()

	return {"name": reapplication.name}
