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
from frappe.utils import cint, cstr, escape_html, flt
from frappe.utils import (
    today,
    add_months,
    get_url,
    nowdate,
    getdate,
    get_first_day,
    get_last_day
)
import datetime
from one_fm.processor import sendemail
from one_fm.grd.utils import get_pcc_attestation_fees
from one_fm.grd.processa import cancel_document

# The process script that opens a row's documents. The Preparation process runs it on
# submit; rows added or re-actioned after submit run it here.
CREATE_DOCUMENTS_SCRIPT = "Create Preparation Documents"


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

# The HR Costing master row carries one more component than a Preparation row does.
# Preparation Record has no visa_amount column, so the tuple above stays its contract:
# widening it would set a field that does not exist and drop the value on save.
MASTER_COST_COMPONENT_FIELDS = COST_COMPONENT_FIELDS + ('visa_amount',)

# PCC attestation fees a row carries on top of the cost components. Kept out of
# COST_COMPONENT_FIELDS because the HR Costing master has no such columns.
ATTESTATION_FEE_FIELDS = ('embassy_attestation_fee', 'mofa_fee', 'pcc_translation_fee')
ROW_TOTAL_FIELDS = COST_COMPONENT_FIELDS + ATTESTATION_FEE_FIELDS
OVERSEAS_ACTIONS = ('Overseas', 'Overseas (Government)')

# The Actions whose master fee row is keyed by the number of years as well as the Action.
# Mirrors the depends_on the costing table already puts on its No. of Years field.
YEAR_SCOPED_ACTIONS = ('Renewal (Kuwaiti)', 'Renewal Expat')

# WI-002092: the fees a multi-year renewal pays once per year. The work permit, the medical
# insurance and the residency stamp are each issued for a year at a time, so renewing for
# three buys three of each.
#
# The civil ID is deliberately absent: one card is issued for the whole period, whatever it
# costs, so multiplying it would charge the employee for cards that were never printed.
#
# WI-002179: an extension is bought the same way, by the month rather than by the year, so
# the same three scale and the same one stays flat.
DURATION_SCALED_COST_FIELDS = (
    'work_permit_amount',
    'medical_insurance_amount',
    'residency_stamp_amount',
)

# WI-002179: one Action for every extension, however long it runs for. "Extend 1 month",
# "Extend 2 months" and "Extend 3 months" were three master fee rows saying the same thing
# three times, and adding a fourth duration meant adding a fourth option and a fourth row.
# The duration is a number on the Preparation row now, and the master row holds the monthly
# rate.
EXTENSION_ACTION = 'Extension'

# WI-002181: the one-month extension an incoming candidate's entry visa gets while the rest
# of their onboarding is arranged. It is an Onboarding Action rather than a Renewal one -
# there is nothing to renew yet - and it opens a Residency and nothing else: the candidate
# has no work permit, no insurance and no civil ID for an extension to follow on from.
VISA_EXTENSION_ACTION = 'Visa Extension'

# The two renewal Actions, and the Action that ends an employment. Named because
# handle_renewal_changes compared against the literal "Renewal" - a value the Action field
# has never offered - so every transition it was written to handle was unreachable.
RENEWAL_ACTIONS = ('Renewal Expat', 'Renewal (Kuwaiti)')
CANCELLATION_ACTION = 'Cancellation'

# Everything a Preparation opens for one row, dependents first. Medical Insurance reads its
# permit, so it goes before the Work Permit. The overseas pair were missing from the
# cancellation list, which left a Medical Appointment and a PCC Attestation behind for a row
# that no longer asks for either.
BATCH_DOCUMENTS = (
    'Medical Appointment',
    'PCC Attestation',
    'Residency',
    'PACI',
    'Medical Insurance',
    'Work Permit',
)


# WI-002101: the batch type, the series it is named under, and the Actions its rows may
# carry. One table, because the naming and the restriction are two halves of the same
# statement - an Onboarding batch named PRE-ONB- that could still carry a Cancellation row
# would be lying about what it is.
#
# The Action values are the Preparation Record field's own options: WI-002101 writes
# "Renewal (Non Kuwaiti)" and "Extend 1 Month" where the field now has "Renewal Expat"
# (WI-002178) and a single "Extension" (WI-002179). The field's own spelling is what every
# existing row and every lookup keyed on it already uses.
CATEGORIES = {
    'Onboarding': {
        'prefix': 'PRE-ONB-',
        'actions': (
            'Overseas',
            'Overseas (Government)',
            'Local Transfer',
            'New Kuwaiti',
            VISA_EXTENSION_ACTION,
        ),
    },
    'Offboarding': {
        'prefix': 'PRE-OFFB-',
        'actions': ('Cancellation',),
    },
    'Renewal': {
        'prefix': 'PRE-REN-',
        'actions': (
            'Renewal (Kuwaiti)',
            'Renewal Expat',
            EXTENSION_ACTION,
        ),
    },
}

# What a batch with no Category recognised is named under. Reachable only through a record
# whose Category was removed from the options after it was made; a new one cannot save
# without one.
FALLBACK_PREFIX = 'PRE-'


# The order the legal steps run in. A row's Current Stage is the first of them that is not
# Completed.
SUB_DOCUMENT_SEQUENCE = ("Work Permit", "Medical Insurance", "Residency", "PACI")


COMPLETED = "Completed"


def _state_label(document):
    """The state a document is in, as the row shows it. A cancelled document says so."""
    if document.get("docstatus") == 2:
        return "Cancelled"
    if document.get("workflow_state"):
        return document.get("workflow_state")
    return "Submitted" if document.get("docstatus") == 1 else "Draft"


def current_stage(documents):
    """The stage a candidate is at, from the latest document of each kind they have.

    `documents` is a list of dicts with doctype, name, workflow_state and docstatus. Pure:
    it reads nothing and writes nothing.

    The stage is the first document in the legal sequence that is not Completed. Once every
    document that exists is Completed, the last of them is the stage. Returns a dict with
    ref_doctype, ref_name and ref_doctype_status ("<DocType> - <state>"), or None when no
    document in the sequence exists.
    """
    latest = {}
    for document in documents or []:
        if document.get("doctype") in SUB_DOCUMENT_SEQUENCE:
            latest[document["doctype"]] = document

    present = [latest[doctype] for doctype in SUB_DOCUMENT_SEQUENCE if doctype in latest]
    if not present:
        return None

    chosen = present[-1]
    for document in present:
        if _state_label(document) != COMPLETED:
            chosen = document
            break

    return {
        "ref_doctype": chosen["doctype"],
        "ref_name": chosen.get("name"),
        "ref_doctype_status": "{0} - {1}".format(chosen["doctype"], _state_label(chosen)),
    }


def refresh_row_stage(preparation, employee):
    """Recompute the Current Stage of the Preparation row for this employee.

    Reads the latest document of each kind, cancelled ones included, and writes the result
    on the row. A row with no document behind it is left as it was.

    Written with db.set_value on the child row - the row belongs to a submitted
    Preparation, and a stage arriving here should not need permission to edit one. The
    label is stored verbatim, not translated.
    """
    if not preparation or not employee:
        return

    row = frappe.db.get_value(
        "Preparation Record",
        {
            "parent": preparation,
            "parenttype": "Preparation",
            "employee": employee,
        },
        "name",
    )
    if not row:
        return

    documents = []
    for doctype in SUB_DOCUMENT_SEQUENCE:
        found = frappe.get_all(
            doctype,
            filters={"preparation": preparation, "employee": employee},
            fields=["name", "workflow_state", "docstatus"],
            order_by="creation desc",
            limit=1,
        )
        if found:
            documents.append(dict(found[0], doctype=doctype))

    stage = current_stage(documents)
    if not stage:
        return

    frappe.db.set_value("Preparation Record", row, stage, update_modified=False)


def update_row_reference(doc, method=None):
    """Refresh the Current Stage of the Preparation row this sub-document belongs to.

    Hung off each sub-document's save, cancel and delete.
    """
    if not doc.get("preparation") or not doc.get("employee"):
        return
    if doc.doctype not in SUB_DOCUMENT_SEQUENCE:
        return

    refresh_row_stage(doc.preparation, doc.employee)


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
            values = attestation_fees_for_row(row.renewal_or_extend, row.nationality)
            row.update(values)
            values['total_amount'] = sum(flt(row.get(field)) for field in ROW_TOTAL_FIELDS)
            if self.docstatus == 1:
                row.db_set(values)
            else:
                row.total_amount = values['total_amount']

        doc_total = sum(flt(row.total_amount) for row in self.preparation_record)
        frappe.db.set_value(self.doctype,self.name,'total_payment',doc_total)
        self.set('total_payment', doc_total)

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

    @frappe.whitelist()
    def set_renewal_for_all_preparation_record(self, renew_all: int | str):
        renew_all = cint(renew_all)
        no_of_years = "1 Year"

        # Set the costing of renewal for an year in preparation record
        for preparation in self.preparation_record:
            # Get costing of renewal for an year
            costing, extension_type = get_renewal_extension_cost_for_employee(preparation.employee, no_of_years)

            preparation.renewal_or_extend = extension_type if renew_all else ""
            preparation.no_of_years = no_of_years if renew_all else ""
            # "Renew all" makes every row a renewal, which is priced by the year. A months
            # value left on the row from an extension is hidden but not harmless - it is
            # what the fees would be multiplied by if the Action were switched back.
            preparation.no_of_months = ""
            # A nationality with no master row configured used to fail here on
            # `None.work_permit_amount`, taking the whole "renew all" action down with it
            # (WI-002031). The row is left at zero instead, which the operator can see and
            # fill, and the totals below stay consistent with it.
            costing = costing or frappe._dict()
            for field in COST_COMPONENT_FIELDS:
                preparation.set(field, flt(costing.get(field)) if renew_all else 0)
            preparation.update(
                attestation_fees_for_row(preparation.renewal_or_extend, preparation.nationality)
            )
            preparation.total_amount = sum(
                flt(preparation.get(field)) for field in ROW_TOTAL_FIELDS
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
                new_row['renewal_or_extend'] = EXTENSION_ACTION
                new_row['no_of_months'] = "3 Months"
            else:
                new_row['renewal_or_extend'] = "Renewal Expat"
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
    "Renewal (Kuwaiti)" and "Renewal Expat". The filter was therefore dead, and a
    renewal with three configured rows (1, 2 and 3 Years) got whichever the database
    handed back first. The years now scope the lookup for the two renewal Actions, which
    are the ones whose master rows are keyed by it.

    Deliberately not scoped by years for any other Action: the field is hidden for them
    but not cleared, so a row switched from Renewal Expat to Extension still
    carries "1 Year", and filtering on it would find nothing and quietly return no fees.
    """
    if not frappe.has_permission('Preparation', 'write'):
        frappe.throw(_("Not permitted to read the GRD renewal and extension costing."),
                     frappe.PermissionError)

    if renewal_or_extend in YEAR_SCOPED_ACTIONS and not no_of_years:
        return False

    # The years narrow the lookup for the two renewal Actions only. The field is hidden for
    # an extension but not cleared, so a row switched from a renewal still carries "1 Year",
    # and filtering an extension by it would find nothing and quietly return no fees.
    scoped_years = no_of_years if renewal_or_extend in YEAR_SCOPED_ACTIONS else None
    result = _master_fee_rows(renewal_or_extend, scoped_years)

    # WI-002092: nothing configured at that duration, so the Action's own row is used
    # whatever duration it is filed under.
    #
    # The years used to have to match exactly, which meant a renewal configured as a
    # "3 Years" row fetched nothing at all for a row asking for one year - and the browser,
    # having already cleared the four fee fields, left the operator looking at zeros with no
    # explanation. The duration that decides the cost is the one on the Preparation row; the
    # master row supplies the rate, and which duration it happens to be filed under is a
    # detail of how the table is keyed.
    if not result and scoped_years:
        result = _master_fee_rows(renewal_or_extend)

    if result:
        return result[0]


def _master_fee_rows(renewal_or_extend, no_of_years=None):
    """The master fee rows for an Action, optionally narrowed to one duration."""
    Cost = DocType('GRD Renewal Extension Cost')
    query = (
        frappe.qb.from_(Cost)
        .select('*')
        .where(Cost.parent == 'HR Settings')
        .where(Cost.parenttype == 'HR Settings')
        .where(Cost.renewal_or_extend == renewal_or_extend)
    )
    if no_of_years:
        query = query.where(Cost.no_of_years == no_of_years)

    return query.run(as_dict=True)

def duration_in(duration):
    """How many periods "2 Years" or "2 Months" means (WI-002092, WI-002179).

    Anything unparseable is one: the fields offer "1 Year"/"2 Years"/"3 Years" and
    "1 Month"/"2 Months"/"3 Months", and a row that somehow carries something else should be
    charged the single-period rate rather than nothing at all.
    """
    periods = cint(cstr(duration).split()[0]) if duration else 0
    return periods or 1


@frappe.whitelist()
def get_preparation_row_costing(
    renewal_or_extend: str, no_of_years: str = None, no_of_months: str = None,
    nationality: str = None
):
    """The fees a Preparation row should carry for this Action and duration (WI-002092).

    The master row in HR Settings holds the rate for one period. A renewal taken for two or
    three years pays the work permit, the medical insurance and the residency stamp once per
    year, so those are multiplied out here - and the civil ID is not, because one card is
    issued for the whole period.

    WI-002179: an extension is the same arithmetic on a shorter period. One "Extension" row
    in HR Settings holds the monthly rate, and the number of months on the Preparation row
    is what it is multiplied by - so a duration nobody configured a row for still costs the
    right amount, which three fixed "Extend N months" options could never do.

    Scaled here rather than in the master lookup so that lookup keeps returning what HR
    Settings actually holds: the master table's own Total Amount is the rate for one period,
    and the two would otherwise disagree about what a row means.

    Called by the form as well as by the "renew all" action, so the browser and the server
    cannot scale a row differently.
    """
    costing = get_grd_renewal_extension_cost(renewal_or_extend, no_of_years)
    if not costing:
        return costing

    costing = dict(costing)
    costing.update(attestation_fees_for_row(renewal_or_extend, nationality))
    if renewal_or_extend in YEAR_SCOPED_ACTIONS:
        periods = duration_in(no_of_years)
    elif renewal_or_extend == EXTENSION_ACTION:
        periods = duration_in(no_of_months)
    else:
        return costing

    for field in DURATION_SCALED_COST_FIELDS:
        costing[field] = flt(costing.get(field)) * periods

    return costing


def attestation_fees_for_row(renewal_or_extend, nationality):
    """The PCC attestation fees a Preparation row carries, keyed by fieldname.

    Only the Overseas Actions pay them; every other Action gets 0 so a hidden stale value
    cannot inflate the total. The amounts come from the same lookup PCC Attestation uses.
    """
    if renewal_or_extend not in OVERSEAS_ACTIONS:
        return dict.fromkeys(ATTESTATION_FEE_FIELDS, 0.0)

    fees = get_pcc_attestation_fees(nationality)
    return {
        'embassy_attestation_fee': fees.embassy_fee,
        'mofa_fee': fees.mofa_fee,
        'pcc_translation_fee': fees.translation_fee,
    }


def handle_creation_of_grd_docs(row,source):
    """Open the documents a row added or re-actioned after submit calls for.

    The process is finished by then, so the script it ran on submit is run here, for this
    row only, the way a script task runs it. The rule stays in the script the process
    owner maintains.
    """
    from one_bpmn.one_bpmn.engine import _check_script_permissions

    script = frappe.db.get_value("Server Script", CREATE_DOCUMENTS_SCRIPT, "script")
    if script is None:
        frappe.throw(_("Server Script {0} is missing. Import the Preparation Lifecycle configuration.").format(CREATE_DOCUMENTS_SCRIPT))
    _check_script_permissions(script, CREATE_DOCUMENTS_SCRIPT)

    preparation = frappe.get_doc("Preparation", source)
    task_data = {"row_names": [row.name]}
    exec(script, {  # noqa: S102
        **task_data,
        "__builtins__": __builtins__,
        "frappe": frappe,
        "doc": preparation,
        "task_data": task_data,
        "result": {},
        "context_doctype": preparation.doctype,
        "context_docname": preparation.name,
    })


def handle_renewal_changes(old_,new_,source):
    """Re-open the documents a row's new Action calls for when the Action is changed.

    HD-1873958: row 41 of PRE-REN-2026-00008 had to go from "Renewal Expat" to
    "Extension", and there was no safe way to do it. The three branches here compared the
    Action against the literal "Renewal", which the field has never offered - its renewal
    options are "Renewal Expat" and "Renewal (Kuwaiti)" - so every one of them was
    unreachable and changing an Action after submit quietly did nothing. The row said
    Extension while the four documents a renewal opens stayed behind it, including a
    PACI and a Work Permit nobody was going to apply for.

    Rebuilt rather than patched transition by transition: `handle_creation_of_grd_docs`
    already knows what every Action opens, so clearing what the old Action opened and
    letting it open the new set covers every pair of Actions, including the reverse
    direction, which the old third branch got wrong anyway - it created a renewal's four
    documents on top of the extension's Residency instead of replacing it.

    A row still holding a document the GRD operator has already submitted is left alone:
    `cancel_delete_doc` force-deletes, and an Action change is not worth destroying work
    somebody has done. The operator is told, and handles those by hand.
    """
    if old_.renewal_or_extend == new_.renewal_or_extend:
        return

    if new_.renewal_or_extend == CANCELLATION_ACTION:
        handle_cancelation(source,new_)
        return

    in_progress = submitted_batch_documents(source,new_)
    if in_progress:
        report_action_change_blocked(new_,in_progress)
        return

    handle_cancelation(source,new_)
    handle_creation_of_grd_docs(new_,source)


def submitted_batch_documents(source,row):
    """The documents this batch opened for a row that have left Draft.

    Returns `(doctype, name)` pairs. Only `docstatus` is read: the GRD workflows run a
    document through most of its states while it is still a draft, so a submitted or
    cancelled document is the one unambiguous signal that the process has moved past the
    point where deleting it is free.
    """
    in_progress = []
    for doctype in BATCH_DOCUMENTS:
        in_progress += [
            (doctype, each.name)
            for each in frappe.get_all(
                doctype,
                filters={'preparation': source, 'employee': row.employee, 'docstatus': ['!=', 0]},
                fields=['name'],
            )
        ]
    return in_progress


def report_action_change_blocked(row,in_progress):
    """Say which documents stopped the row being rebuilt, and that the Action still moved.

    The Action is an `allow_on_submit` field, so by the time this runs the new value is
    already on the row - there is nothing to roll back, and throwing would only lose the
    rest of the save. What the operator needs is the list.
    """
    items = "".join(
        "<li>{0} <b>{1}</b></li>".format(escape_html(doctype), escape_html(name))
        for doctype, name in in_progress
    )
    frappe.msgprint(
        "<p>{intro}</p><ul>{items}</ul><p class=\"text-muted small\">{footer}</p>".format(
            intro=_("The Action for {0} was changed, but the documents already opened for them could not be replaced - these have been submitted:").format(
                escape_html(cstr(row.full_name or row.employee))
            ),
            items=items,
            footer=_("Cancel or complete them, then set the Action again."),
        ),
        title=_("Documents Not Replaced"),
        indicator="orange",
        wide=True,
    )


def handle_updates(method_dict):
    for one in method_dict['to_create']:
        handle_creation_of_grd_docs(one['row'],one['source'])
    for one in method_dict['to_cancel']:
        handle_cancelation(one['source'],one['row'])
    for one in method_dict['to_renew']:
        handle_renewal_changes(one['old_row'],one['new_row'],one['source'])
        
        
            
def handle_cancelation(source,row):
    """Cancel every GRD document this Preparation opened for an employee.

    Listed in BATCH_DOCUMENTS rather than here, because the Action change path clears the
    same set: the two were written separately and the overseas Actions' Medical
    Appointment and PCC Attestation were only ever in one of them.

    `handle_extension`, which cleared three of these for a row moving to Extension, is
    gone: its only caller was the unreachable first branch of `handle_renewal_changes`,
    and the rebuild there now clears the whole set and re-opens what the new Action asks
    for - which an extension's own Residency has to be, since the one left standing was
    categorised Renewal and dated for one.
    """
    for doctype in BATCH_DOCUMENTS:
        cancel_delete_doc(doctype,source,row)

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
                cancel_document(doc, _("{0} no longer needs this document").format(source))
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
        extension_type = "Renewal Expat"
    
    # The row's fees, not the master row's: a multi-year renewal pays the annual ones once
    # per year (WI-002092).
    return get_preparation_row_costing(extension_type, no_of_years), extension_type