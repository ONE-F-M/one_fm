# class Preparation(Document):
# 	pass
# -*- coding: utf-8 -*-
# Copyright (c) 2021, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.query_builder import DocType
from frappe.utils import flt
from frappe.utils import (
    today,
    add_months,
    get_url,
    nowdate,
    getdate,
    now_datetime,
    get_first_day,
    get_last_day
)
import datetime
from one_fm.grd.doctype.work_permit import work_permit
from one_fm.grd.doctype.medical_insurance import medical_insurance
from one_fm.grd.doctype.residency_payment_request import residency_payment_request
from one_fm.grd.doctype.residency import residency
from one_fm.grd.doctype.paci import paci
from one_fm.grd.doctype.fingerprint_appointment import fingerprint_appointment
from one_fm.processor import sendemail

# WI-001824: which documents each of the new Actions generates on submit. An Action
# absent from here keeps its existing behaviour, which the renewal and extend paths
# below still own.
#
# New Kuwaiti gets a Work Permit and nothing else: a Kuwaiti has no residency, no civil
# ID application and no medical insurance process to open.
#
# A key means "open this document"; its value is the government classification that
# document is opened under. WI-002033: every value is stated here rather than left to the
# creator to derive. Three of the four used to be None, meaning "Medical Insurance will
# map the status off the Work Permit type and Residency will map the category off the
# Action" - so this table, the one place an operator or a reviewer looks to see what an
# Action produces, did not actually say what three of the four documents would get, and a
# change to either creator's own mapping silently changed what Preparation produced.
#
# The creators keep their derivations for their other callers, which do not come through a
# Preparation row and have nothing to pass. Residency still takes its application date
# from MOI_CATEGORY_BY_ACTION; only the category is handed to it.
NEW_ACTION_DOCUMENTS = {
    "New Kuwaiti": {
        "work_permit": "New Kuwaiti",
    },
    "Overseas": {
        "work_permit": "Overseas",
        "medical_insurance": "New",
        "residency": "First Time",
        "paci": "New Application",
    },
    # WI-002024: the same overseas hire, but against a government contract file rather
    # than a private one. Every document it opens is the one Overseas opens - what
    # differs is the work permit fee, which PAM charges at the lower government project
    # rate, so the Action has to be distinguishable at the point the fee is fetched and
    # on the permit itself. Splitting it here rather than adding a flag beside Overseas
    # keeps it a single choice in the operator's Action dropdown, which is where the
    # distinction is actually made.
    "Overseas (Government)": {
        "work_permit": "Overseas (Government)",
        "medical_insurance": "New",
        "residency": "First Time",
        "paci": "New Application",
    },
    # The process map groups Local Transfer with Overseas and the non-Kuwaiti renewal:
    # all four documents, opened by the Preparation itself. There is no Transfer Paper in
    # that path, which is why the transfer side of the Work Permit lifecycle had to stop
    # assuming one.
    "Local Transfer": {
        "work_permit": "Local Transfer",
        "medical_insurance": "Local Transfer",
        "residency": "Transfer",
        "paci": "Transfer",
    },
}


# WI-002031: the fee components a master row and a Preparation row both carry, and which
# the Total Amount on each is the sum of. Named once because HR Settings and Preparation
# have to agree on the list - a component added to one and not the other silently drops
# out of the total on the other side.
COST_COMPONENT_FIELDS = (
    'work_permit_amount',
    'medical_insurance_amount',
    'residency_stamp_amount',
    'civil_id_amount',
)

# The Actions whose master fee row is keyed by the number of years as well as the Action.
# Mirrors the depends_on the costing table already puts on its No. of Years field.
YEAR_SCOPED_ACTIONS = ('Renewal (Kuwaiti)', 'Renewal (Non-Kuwaiti)')


# WI-002101: the batch type, the series it is named under, and the Actions its rows may
# carry. One table, because the naming and the restriction are two halves of the same
# statement - an Onboarding batch named PRE-ONB- that could still carry a Cancellation row
# would be lying about what it is.
#
# The Action values are the Preparation Record field's own options, spelling included:
# WI-002101 writes "Renewal (Non Kuwaiti)" and "Extend 1 Month" where the field has
# "Renewal (Non-Kuwaiti)" and "Extend 1 month". The field's spelling is what every existing
# row and every lookup keyed on it already uses.
CATEGORIES = {
    'Onboarding': {
        'prefix': 'PRE-ONB-',
        'actions': ('Overseas', 'Overseas (Government)', 'Local Transfer', 'New Kuwaiti'),
    },
    'Offboarding': {
        'prefix': 'PRE-OFFB-',
        'actions': ('Cancellation',),
    },
    'Renewal': {
        'prefix': 'PRE-REN-',
        'actions': (
            'Renewal (Kuwaiti)',
            'Renewal (Non-Kuwaiti)',
            'Extend 1 month',
            'Extend 2 months',
            'Extend 3 months',
        ),
    },
}

# What a batch with no Category recognised is named under. Reachable only through a record
# whose Category was removed from the options after it was made; a new one cannot save
# without one.
FALLBACK_PREFIX = 'PRE-'


# WI-002093: the order the legal steps run in, so a row can say which one the candidate has
# reached. Furthest along wins - the sequence only moves forward, and what an operator wants
# to see is progress, not the last document anybody happened to touch.
SUB_DOCUMENT_SEQUENCE = ("Work Permit", "Medical Insurance", "Residency", "PACI")


def update_row_reference(doc, method=None):
    """Point a Preparation row at the sub-document its candidate has reached (WI-002093).

    Hung off each sub-document's own save, so the status on the row is the status on the
    document rather than a snapshot from whenever the Preparation was last touched.

    Only ever moves forward: a Medical Insurance saving does not pull the row back from the
    PACI it had already reached. That is what makes it a progress column and not a
    last-touched column.

    Written with db.set_value on the child row - the row belongs to a submitted Preparation,
    and a status arriving here should not need permission to edit one.
    """
    if not doc.get("preparation") or not doc.get("employee"):
        return

    try:
        position = SUB_DOCUMENT_SEQUENCE.index(doc.doctype)
    except ValueError:
        return

    row = frappe.db.get_value(
        "Preparation Record",
        {
            "parent": doc.preparation,
            "parenttype": "Preparation",
            "employee": doc.employee,
        },
        ["name", "ref_doctype"],
        as_dict=True,
    )
    if not row:
        return

    if row.ref_doctype in SUB_DOCUMENT_SEQUENCE:
        if SUB_DOCUMENT_SEQUENCE.index(row.ref_doctype) > position:
            return

    frappe.db.set_value(
        "Preparation Record",
        row.name,
        {
            "ref_doctype": doc.doctype,
            "ref_name": doc.name,
            "ref_doctype_status": doc.get("workflow_state") or "",
        },
        update_modified=False,
    )


def category_for_action(action):
    """The Category a batch carrying this Action belongs to, or None (WI-002101).

    The inverse of the table above. Every Action belongs to exactly one Category, which is
    what makes a single Category per batch workable in the first place.
    """
    for category, rules in CATEGORIES.items():
        if action in rules['actions']:
            return category


@frappe.whitelist()
def get_actions_for_category(category: str):
    """The Actions a batch of this Category may carry (WI-002101).

    Read by the form to narrow the Action dropdown, and by nothing else - the server does
    not take the browser's word for it, it re-checks on validate.
    """
    return list(CATEGORIES.get(category, {}).get('actions', ()))


class Preparation(Document):
    def autoname(self):
        """Name the batch after what it is (WI-002101).

        PRE-ONB-, PRE-OFFB- or PRE-REN- and the year, so the series says at a glance which
        kind of batch a document is. WI-002093 writes the offboarding prefix as PRE-OFF-;
        WI-002101, which is the item that specifies the naming in full, writes PRE-OFFB-,
        and that is what is used here.

        Records named under the old format:PRE-{posting_date}-{######} keep their names.
        """
        prefix = CATEGORIES.get(self.category, {}).get('prefix', FALLBACK_PREFIX)
        self.name = make_autoname(prefix + '.YYYY.-.#####')

    def validate_actions_match_category(self):
        """Refuse a row whose Action does not belong to this kind of batch (WI-002101).

        The form narrows the dropdown, but the dropdown is not the rule: rows arrive from
        the monthly schedule, from a data import and from the API as well, and a
        Cancellation sitting in an Onboarding batch would open the wrong documents on
        submit.
        """
        allowed = CATEGORIES.get(self.category, {}).get('actions')
        if not allowed:
            return

        wrong = [
            row for row in self.preparation_record
            if row.renewal_or_extend and row.renewal_or_extend not in allowed
        ]
        if not wrong:
            return

        rows = '<br>'.join(
            _('Row {0}: {1}').format(row.idx, frappe.bold(row.renewal_or_extend)) for row in wrong
        )
        frappe.throw(
            _('A {0} batch cannot carry these Actions:<br>{1}<br><br>Allowed: {2}').format(
                frappe.bold(_(self.category)), rows, ', '.join(allowed)
            ),
            title=_('Action Does Not Match the Category'),
        )

    def update_total_amount(self):
        """Derive each row's Total Amount from its components, then the document total.

        The row total was summed only in the browser (WI-002031), which left the field -
        read-only, and the number finance is emailed - holding whatever the last client to
        touch the row happened to compute. A row whose components were edited after submit,
        or filled by any path other than the Action dropdown, kept a total that did not
        match its own parts.

        Rows are written with `db_set` once the document is submitted, because
        `on_update_after_submit` runs after the child rows are already saved and a plain
        assignment there would be discarded.
        """
        for row in self.preparation_record:
            row_total = sum(flt(row.get(field)) for field in COST_COMPONENT_FIELDS)
            if self.docstatus == 1:
                row.db_set('total_amount', row_total)
            else:
                row.total_amount = row_total

        doc_total = sum(flt(row.total_amount) for row in self.preparation_record)
        frappe.db.set_value(self.doctype,self.name,'total_payment',doc_total)
        self.total_payment = doc_total

    def on_update_after_submit(self):
        self.compare_preparation_record()
        self.update_total_amount()
    
    def compare_preparation_record(self):
        """Compare the data of preparation record child table before it was saved with the most updated version
        and flag changes
        """
        count = 0
        method_dict = {
            'to_cancel':[],
            'to_renew':[],
            'to_create':[]}
        old_preparation_record = {}
        new_preparation_record = {}
        old_doc = self.get_doc_before_save()
        for each in old_doc.preparation_record: 
            old_preparation_record[each.name] =  each
        old_row_ids = [i.name for i in old_doc.preparation_record ]
        for one in self.preparation_record:
            new_preparation_record[one.name] =  one
        new_row_ids = [i.name for i in self.preparation_record ]
        
        for ind in old_row_ids: #Find Removed rows 
            if ind not in new_row_ids: # Delete for this employee
                method_dict['to_cancel'].append({'source':self.name,'row':old_preparation_record.get(ind)})
                count+=1
            else:
                if old_preparation_record.get(ind).get('renewal_or_extend')!=new_preparation_record.get(ind).get('renewal_or_extend'):
                    method_dict['to_renew'].append({'old_row':old_preparation_record.get(ind),'new_row':new_preparation_record.get(ind),'source':self.name})
                    count+=1
        for each in new_row_ids: #Find New rows added
            if each not in old_row_ids:
                method_dict['to_create'].append({'row':new_preparation_record.get(each),'source':self.name})
                count+=1
        if count>10:
            frappe.enqueue(handle_updates,timeout = 600,method_dict = method_dict)
        else:
            handle_updates(method_dict)
                 
            
    def validate(self):
        self.set_grd_values()
        self.set_hr_values()
        self.validate_actions_match_category()
        validate_preparation_table(self)
        self.update_total_amount()
        
    def set_grd_values(self):
        """
		runs: `validate`
		param: preparation object
		This method is fetching values of grd supervisor or operator for renewal from HR Settings
		"""
        if not self.grd_supervisor:
            self.grd_supervisor = frappe.db.get_single_value("HR Settings", "default_grd_supervisor")
        if not self.grd_operator:
            self.grd_operator = frappe.db.get_single_value("HR Settings", "default_grd_operator")

    def set_hr_values(self):
        """
		runs: `validate`
		param: preparation object
		This method is fetching values of hr user
		"""
        if not self.hr_user:
            self.hr_user = frappe.db.get_single_value("Hiring Settings","default_hr_user")

    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        validate_preparation_table(self)
        self.db_set('submitted_by', frappe.session.user)
        self.db_set('submitted_on', now_datetime())
        self.recall_create_work_permit_renewal() ## create work permit record for renewals
        self.recall_create_medical_insurance_renewal() # create medical insurance record for renewals
        self.recall_create_moi_renewal_and_extend() # create moi record for all employee
        self.recall_create_paci() # create paci record for all
        # self.recall_create_fp()# create fp record for all
        self.recall_create_documents_for_new_actions() # WI-001824: New Kuwaiti / Overseas
        self.send_notifications()

    def recall_create_documents_for_new_actions(self):
        create_documents_for_new_actions(self.name)

    def validate_mandatory_fields_on_submit(self):
        mandatory_fields = []
        mandatory_fields_reqd = False
        for item in self.preparation_record:#each item in the preparation_record row
            if not item.renewal_or_extend:#column not filled
                mandatory_fields_reqd = True
                mandatory_fields.append(item.idx)
        if len(mandatory_fields) > 0:
            message = 'Mandatory fields required in Preparation to Submit<br><br><ul>'
            for mandatory_field in mandatory_fields:
                message += '<li>' +'<p> fill the renewal or extend field for row number {0}</p>''</li>'.format(mandatory_field)
            message += '</ul>'
            frappe.throw(message)


    def recall_create_work_permit_renewal(self):
        work_permit.create_work_permit_renewal(self.name)

    def recall_create_medical_insurance_renewal(self):
        medical_insurance.valid_work_permit_exists(self.name)

    def recall_create_moi_renewal_and_extend(self):
        residency.set_employee_list_for_moi(self.name)

    def recall_create_paci(self):
        paci.create_PACI_renewal(self.name)

    def recall_create_fp(self):
        fingerprint_appointment.creat_fp_record(self.name)

    def send_notifications(self):
        """
            runs: `on_submit`
            This method will notifiy operator to apply for the wp, mi, moi, paci, fp that are created for all employees in the list
        """
        if self.grd_operator:
            page_link = get_url(self.get_url())
            message = "<p>Records are created<a href='{0}'>{1}</a>.</p>".format(page_link, self.name)
            subject = 'Records are created for WP, MI, MOI, PACI, and FP'
            create_notification_log(subject, message, [self.grd_operator], self)

        # The costing mail renders a PDF and hands it to the mail server, and neither belongs
        # inside the submit transaction. wkhtmltopdf died with SIGSEGV on staging and took the
        # whole submit down with it - but the Work Permit, Medical Insurance, MOI and PACI
        # records created above each commit as they go, so they survived while the Preparation
        # rolled back to draft, and re-submitting created them a second time. Queued after the
        # commit so a broken PDF is an Error Log entry, not a failed submit.
        frappe.enqueue(
            'one_fm.grd.doctype.preparation.preparation.send_costing_notification',
            queue='short',
            enqueue_after_commit=True,
            preparation=self.name
        )

    @frappe.whitelist()
    def set_renewal_for_all_preparation_record(self, renew_all):
        no_of_years = "1 Year"

        # Set the costing of renewal for an year in preparation record
        for preparation in self.preparation_record:
            # Get costing of renewal for an year
            costing, extension_type  = get_renewal_extension_cost_for_employee(preparation.employee, no_of_years)

            preparation.renewal_or_extend = extension_type if renew_all else ""
            preparation.no_of_years = no_of_years if renew_all else ""
            # A nationality with no master row configured used to fail here on
            # `None.work_permit_amount`, taking the whole "renew all" action down with it
            # (WI-002031). The row is left at zero instead, which the operator can see and
            # fill, and the totals below stay consistent with it.
            costing = costing or frappe._dict()
            for field in COST_COMPONENT_FIELDS:
                preparation.set(field, flt(costing.get(field)) if renew_all else 0)
            preparation.total_amount = sum(
                flt(preparation.get(field)) for field in COST_COMPONENT_FIELDS
            )

# Calculate the date of the next month (First & Last) (monthly cron in hooks)
def auto_create_preparation_record():
    """
    runs: at the Preparation Record Creation Day configured in the HR Settings
    This method will create preparation record that contain list of all employees that their residency expiry date will be between the first and the last date of the next month
    This record will go to HR user to set value for each employee either renewal or extend and on the submit of this record it will ask for hr permission and approval.
    Then, it will create wp, mi, moi, and paci records for all employees in the list.
    """
    preparation_record_creation_day = frappe.db.get_single_value("HR Settings", "preparation_record_creation_day")
    if preparation_record_creation_day and preparation_record_creation_day > 0:
        preparation_record_creation_day_date = datetime.date.today().replace(day=preparation_record_creation_day)
        if getdate(preparation_record_creation_day_date) == getdate(today()):
            create_preparation_record()

@frappe.whitelist()
def create_preparation_record():
    """
        This method will create preparation record for next month from the date of execution.
        The record contain list of all employees that their residency expiry date will be between the first and the last date of the next month
        This record will go to HR user to set value for each employee either renewal or extend and on the submit of this record it will ask for hr permission and approval.
    """
   
    doc = frappe.new_doc('Preparation')
    # The monthly batch is a renewal run by definition - it is built from the employees
    # whose residency expires next month - so it names itself PRE-REN- (WI-002101).
    doc.category = 'Renewal'
    doc.posting_date = nowdate()
    first_day = get_first_day(add_months(getdate(today()), 1))
    last_day = get_last_day(getdate(first_day))
    employee_entries = frappe.db.get_list('Employee',
        fields=("residency_expiry_date", "name",'one_fm_nationality','status','relieving_date'),
        filters={
            'residency_expiry_date': ['between', (first_day, last_day)],
            'status': 'Active',
            'under_company_residency':['=', 1]
        }
    )
    employee_entries.sort(key=sort)
    for employee in employee_entries:
        new_row = {"employee": employee.name, "relieving_date": employee.relieving_date}
        
        if employee.one_fm_nationality == "Kuwaiti":
            new_row['renewal_or_extend'] = "Renewal (Kuwaiti)"
        else:
            if employee.relieving_date: 
                new_row['renewal_or_extend'] = "Extend 3 months"
            else:
                new_row['renewal_or_extend'] = "Renewal (Non-Kuwaiti)"
        doc.append("preparation_record", new_row)
            
    doc.save()
    notify_hr(doc)

# sort list based on residency expriy date to be displaied in the table based on their `residency_expiry_date`
def sort(r):
    return r['residency_expiry_date']

def notify_hr(doc):
    page_link = get_url(doc.get_url())
    subject = ("Preparation Record has been created")
    message = "<p>Kindly, Check and Fill The Renewal and Extend Field for Employees whose Residency Will Expire in the Following month <a href='{0}'></a></p>".format(page_link)
    create_notification_log(subject, message, [doc.hr_user], doc)

def notify_request_for_renewal_or_extend():# Notify finance
    filters = {'docstatus': 1}
    preparation_list = frappe.get_doc('Preparation', filters,['name', 'notify_finance_user'])
    page_link = get_url(preparation_list.get_url())
    message = "<p>Please Review the Renewal and Extend List of employee {0}<a href='{1}'></a></p>".format(page_link,preparation_list.name)
    subject = '{0} Renewal and Extend list approved'.format("Prepare Payments")
    send_email(preparation_list, [preparation_list.notify_finance_user], message, subject)
    create_notification_log(subject, message, [preparation_list.notify_finance_user], preparation_list)

def send_costing_notification(preparation):
    """Email the costing print of a submitted Preparation to the user set in HR Settings.

    Runs in the background - see Preparation.send_notifications for why.
    """
    inform_the_costing_to = frappe.db.get_single_value('HR Settings', 'inform_the_costing_to')
    if not inform_the_costing_to:
        return

    doc = frappe.get_doc('Preparation', preparation)
    message = "<p>Records are created<a href='{0}'>{1}</a>.</p>".format(get_url(doc.get_url()), doc.name)
    subject = 'Details of the Preparation Cost for WP, MI, MOI, PACI, and FP'
    print_format = frappe.db.get_single_value('HR Settings', 'costing_print_format') or 'Standard'
    attachments = [frappe.attach_print(doc.doctype, doc.name, file_name=doc.name, print_format=print_format)]
    send_email(doc, [inform_the_costing_to], message, subject, attachments)

def send_email(doc, recipients, message, subject, attachments=None):
    sendemail(
        recipients= recipients,
        subject=subject,
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
        attachments=attachments
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

@frappe.whitelist()
def get_grd_renewal_extension_cost(renewal_or_extend: str, no_of_years: str = None):
    """The master fee breakdown HR Settings holds for an Action (WI-002031).

    Rewritten off `frappe.db.sql` with the Action interpolated into the string. The Action
    arrives from the browser through a whitelisted method, so that was an injection hole
    open to any logged-in user, and the method had no permission check at all. Both are
    closed here: the Query Builder parameterises the value, and the caller has to be
    someone who could fill in a Preparation row, which is the only thing this feeds.

    The old version filtered on the number of years only when the Action was exactly
    "Renewal" - a value the field has not offered since the options became
    "Renewal (Kuwaiti)" and "Renewal (Non-Kuwaiti)". The filter was therefore dead, and a
    renewal with three configured rows (1, 2 and 3 Years) got whichever the database
    handed back first. The years now scope the lookup for the two renewal Actions, which
    are the ones whose master rows are keyed by it.

    Deliberately not scoped by years for any other Action: the field is hidden for them
    but not cleared, so a row switched from Renewal (Non-Kuwaiti) to Extend 1 month still
    carries "1 Year", and filtering on it would find nothing and quietly return no fees.
    """
    if not frappe.has_permission('Preparation', 'write'):
        frappe.throw(_("Not permitted to read the GRD renewal and extension costing."),
                     frappe.PermissionError)

    if renewal_or_extend in YEAR_SCOPED_ACTIONS and not no_of_years:
        return False

    Cost = DocType('GRD Renewal Extension Cost')
    query = (
        frappe.qb.from_(Cost)
        .select('*')
        .where(Cost.parent == 'HR Settings')
        .where(Cost.parenttype == 'HR Settings')
        .where(Cost.renewal_or_extend == renewal_or_extend)
    )
    if renewal_or_extend in YEAR_SCOPED_ACTIONS:
        query = query.where(Cost.no_of_years == no_of_years)

    result = query.run(as_dict=True)
    if result:
        return result[0]

def create_documents_for_new_actions(preparation_name):
    """Generate the sub-documents the New Kuwaiti and Overseas Actions ask for (WI-001824).

    One row at a time, and one row's failure does not stop the rest: the same contract
    the renewal and extend paths already keep, so a single bad employee record cannot
    cost the whole batch its documents.
    """
    preparation = frappe.get_doc('Preparation', preparation_name)

    for row in preparation.preparation_record:
        if row.renewal_or_extend not in NEW_ACTION_DOCUMENTS:
            continue
        try:
            create_documents_for_row(row, preparation_name)
        except Exception:
            frappe.log_error(
                title=f"Error creating GRD documents for {row.employee} in Preparation {preparation_name}",
                message=frappe.get_traceback(),
            )
            continue


def create_documents_for_row(row, preparation_name):
    """Open the documents one Preparation row's Action calls for, in dependency order.

    The Work Permit comes first because Medical Insurance is opened against it - it
    reads the type, the application date and the passport expiry off the permit rather
    than being told them.
    """
    plan = NEW_ACTION_DOCUMENTS[row.renewal_or_extend]
    employee_doc = frappe.get_doc('Employee', row.employee)

    work_permit_doc = work_permit.create_wp_from_preparation(
        employee_doc, plan["work_permit"], preparation_name
    )

    if "medical_insurance" in plan:
        medical_insurance.create_mi_record(
            work_permit_doc, insurance_status=plan["medical_insurance"]
        )

    if "residency" in plan:
        residency.create_moi_record(
            employee_doc, row.renewal_or_extend, preparation_name, category=plan["residency"]
        )

    if "paci" in plan:
        paci.create_PACI(employee_doc, plan["paci"], preparation_name)

    return work_permit_doc


def handle_creation_of_grd_docs(row,source):
    """
            Handle the creation of grd documents for  new rows just added after the submission of a preparation  document
    Args:
        row (dict): dict containing employee information
    """
    # A row added after submit takes the same route as one that was there at submit,
    # or the new Actions would silently create nothing here (WI-001824).
    if row.renewal_or_extend in NEW_ACTION_DOCUMENTS:
        try:
            create_documents_for_row(row, source)
        except Exception:
            frappe.log_error(
                title=f"Error creating New GRD documents for {row.employee}",
                message=frappe.get_traceback(),
            )
        return

    try:
        employee_doc = frappe.get_doc("Employee",row.employee)
        work_permit.create_wp_renewal(employee_doc,row.renewal_or_extend,source)
        frappe.db.commit() #because Medical Insurance depends on the work permit
        medical_insurance.create_mi_record(frappe.get_doc('Work Permit',{'preparation':source,'employee':employee_doc.employee}))
        residency.create_moi_record(employee_doc,row.renewal_or_extend,preparation_name=source)
        paci.create_PACI(employee_doc,row.renewal_or_extend,source)   
    except:
        frappe.log_error(title=f"Error Creating New GRD documents  for {row.employee} </b>",message=frappe.get_traceback()) 
    
    
def handle_renewal_changes(old_,new_,source):
    """
    Handle the changes in  renewal field of a row in the preparation record table 
    Args:
        old (dict): a dict containing details of the old row
        new (dict): a dict containing details of the new row
    """
    if old_.renewal_or_extend == "Renewal" and new_.renewal_or_extend in ['Extend 1 month','Extend 2 months','Extend 3 months']:
        handle_extension(source,new_)
    elif new_.renewal_or_extend == "Cancellation":
        handle_cancelation(source,new_)
    elif new_.renewal_or_extend == "Renewal" and old_.renewal_or_extend != "Renewal":
        handle_creation_of_grd_docs(new_,source)
        #Create for all
        
def handle_updates(method_dict):
    for one in method_dict['to_create']:
        handle_creation_of_grd_docs(one['row'],one['source'])
    for one in method_dict['to_cancel']:
        handle_cancelation(one['source'],one['row'])
    for one in method_dict['to_renew']:
        handle_renewal_changes(one['old_row'],one['new_row'],one['source'])
        
        
            
def handle_extension(source,row):
    """Cancel 3 of the linked GRD documents for an employee"""
    cancel_delete_doc("PACI",source,row)
    cancel_delete_doc("Medical Insurance",source,row)
    cancel_delete_doc("Work Permit",source,row)

def handle_cancelation(source,row):
    """Cancel all the linked GRD documents for an employee"""
    cancel_delete_doc("Residency",source,row)
    cancel_delete_doc("PACI",source,row)
    cancel_delete_doc("Medical Insurance",source,row)
    cancel_delete_doc("Work Permit",source,row)

def cancel_delete_doc(doctype,source,row):
    """
    Loop through a list of records, cancel and delete them
    Args:
        doctype (str): a doctype
        records (dict): a dict of records
    """
    records = frappe.get_all(doctype,{'preparation':source,'employee':row.employee},['docstatus','name'])
    
    for each in records:
        try:
            doc = frappe.get_doc(doctype,each.name)
            doc.flags.ignore_links = 1
            doc.flags.ignore_permissions = 1
            doc.save()
            if each.docstatus == 1:  
                doc.cancel()
            frappe.delete_doc(doctype,each.name,force= True)
        except:
            frappe.log_error(title=f"Error Cancelling and Deleting <b>{doctype} {each.name} </b>",message=frappe.get_traceback())
            
            continue

def validate_preparation_table(doc):
    """Ensure that all the employees in the preparation table are in Active Status"""

    all_active_staff = frappe.get_all("Employee",{'status': ["IN",["Active"]]})
    if all_active_staff:
        all_active_staff_list = [o.name for o in all_active_staff]
        for each in doc.preparation_record:
            if each.employee not in all_active_staff_list:
                frappe.throw(f"The Employee in row <b>{each.idx}</b> <b>{each.full_name}</b> is not Active at the moment")

@frappe.whitelist()
def get_employees_relieving_date(employees):
    """
        Return relieving_date in Employee for each employee.
    """
    if not employees:
        return {}
    if isinstance(employees, str):
        try:
            import json as _json
            employees = _json.loads(employees)
        except Exception:
            employees = [employees]
    if not isinstance(employees, (list, tuple, set)):
        employees = [employees]
    employees = list({e for e in employees if e})  # dedupe & drop falsy
    if not employees:
        return {}

    params = {"employees": tuple(employees)}
    # Single query: Employee + MAX(checkin.date)
    rows = frappe.db.sql(
        """
        SELECT
            e.name AS employee,
            e.relieving_date AS relieving_date
        FROM `tabEmployee` e
        WHERE e.name IN %(employees)s
        """,
        params,
        as_dict=True,
    )

    result = {}
    for r in rows:
        result[r.employee] = {
            "relieving_date": r.relieving_date
        }
    return result

@frappe.whitelist()
def update_preparation_employee_dates(preparation: str):
    """
        Update relieving_date in child rows without making the form dirty.
        Uses frappe.db.set_value (update_modified=False) so the client doc stays clean until reload.
        Returns map of updated rows and data used.
    """
    if not preparation:
        return {}
    doc = frappe.get_doc('Preparation', preparation)
    if doc.is_new():  # cannot update unsaved document rows
        return {'updated_rows': [], 'data': {}}
    employees = [r.employee for r in doc.preparation_record if r.employee]
    if not employees:
        return {'updated_rows': [], 'data': {}}
    data = get_employees_relieving_date(employees)
    updated = []
    for row in doc.preparation_record:
        if not row.employee:
            continue
        info = data.get(row.employee)
        if not info:
            continue
        rel = info.get('relieving_date')
        if row.relieving_date != rel:
            frappe.db.set_value(row.doctype, row.name, {
                'relieving_date': rel
            }, update_modified=False)
            updated.append(row.name)
    return {'updated_rows': updated, 'data': data}

def get_renewal_extension_cost_for_employee(employee, no_of_years = "1 Year"):
    """
        Get renewal/extension cost for an employee based on his nationality
    """
    employee_nationality = frappe.db.get_value("Employee", employee, "one_fm_nationality")

    if employee_nationality == "Kuwaiti":
        extension_type = "Renewal (Kuwaiti)"
    else:
        extension_type = "Renewal (Non-Kuwaiti)"
    
    return get_grd_renewal_extension_cost(extension_type, no_of_years), extension_type