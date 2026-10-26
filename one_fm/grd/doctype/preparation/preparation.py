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
from frappe.utils import cint, cstr, escape_html, flt, strip_html
from frappe.utils import (
    today,
    add_days,
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
from one_fm.grd.doctype.medical_appointment import medical_appointment
from one_fm.grd.doctype.pcc_attestation import pcc_attestation
from one_fm.grd.doctype.fingerprint_appointment import fingerprint_appointment
from one_fm.processor import sendemail
from one_fm.grd.utils import get_nationality_attestation_rule, get_pcc_attestation_fees

# The documents a Preparation row can owe, in the order they have to be opened: Medical
# Insurance reads its type, application date and passport expiry off the Work Permit, so
# the permit exists before it does. The keys are NEW_ACTION_DOCUMENTS' own keys - one
# vocabulary for the plan, the resume and the daily check.
STEP_ORDER = (
    "work_permit",
    "medical_insurance",
    "residency",
    "paci",
    "medical_appointment",
    "pcc_attestation",
)

STEP_DOCTYPES = {
    "work_permit": "Work Permit",
    "medical_insurance": "Medical Insurance",
    "residency": "Residency",
    "paci": "PACI",
    "medical_appointment": "Medical Appointment",
    "pcc_attestation": "PCC Attestation",
}

# The Actions the renewal creators act on, named because expected_steps_for_row has to
# mirror the conditions those creators apply.
RENEWAL_EXPAT = "Renewal Expat"
RENEWAL_KUWAITI = "Renewal (Kuwaiti)"
RENEWAL_ACTIONS = (RENEWAL_EXPAT, RENEWAL_KUWAITI)
KUWAITI = "Kuwaiti"

# Residency's own dispatcher owns the Actions not in here ("anything that is not handled
# on submit is an extension"), so the expectation has to read the same tuple rather than
# a copy of it that can drift.
ACTIONS_HANDLED_ON_SUBMIT = residency.ACTIONS_HANDLED_ON_SUBMIT

# How many rows a Preparation can carry and still have its documents opened inside the
# submit request. A row takes about four seconds, so ten is around forty seconds - well
# inside the web server's 120-second timeout, which is what killed PRE-ONB-2026-00008's
# 27-row submit (HD-1898774). Anything larger is queued.
INLINE_ROW_LIMIT = 10

# A batch of 90 rows opens close to 540 documents at roughly four seconds a row, so the
# job is given half an hour rather than the long queue's default.
CREATION_JOB_TIMEOUT = 1800

# HD-1898774: the event the form listens on to pull the stages in once a run has written
# them. refresh_row_stage writes the row with db.set_value and update_modified=False, so
# nothing about the write reaches a browser on its own - not the document the submit
# response carries, and not the parent's timestamp that would make the client refetch.
DOCUMENTS_CREATED_EVENT = "preparation_documents_created"

# How far back the daily check looks. Long enough to catch a batch submitted before a
# weekend, short enough that it is not re-reading last quarter's every night.
GAP_CHECK_WINDOW_DAYS = 30

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
#
# WI-002095: the two overseas Actions also open the medical the candidate has to pass and
# the attestation of their police clearance - the two steps of overseas onboarding the GRO
# was still raising by hand. No Fingerprint Appointment is opened for any Action: the
# fingerprint is taken once the candidate is in the country and holds a civil ID, so it is
# not part of what a Preparation generates.
NEW_ACTION_DOCUMENTS = {
    "New Kuwaiti": {
        "work_permit": "New Kuwaiti",
    },
    "Overseas": {
        "work_permit": "Overseas",
        "medical_insurance": "New",
        "residency": "First Time",
        "paci": "New Application",
        "medical_appointment": "First Time",
        "pcc_attestation": "Overseas",
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
        "medical_appointment": "First Time",
        "pcc_attestation": "Overseas (Government)",
    },
    # The process map groups Local Transfer with Overseas and the non-Kuwaiti renewal:
    # all four documents, opened by the Preparation itself. There is no Transfer Paper in
    # that path, which is why the transfer side of the Work Permit lifecycle had to stop
    # assuming one.
    "Local Transfer": {
        "work_permit": "Local Transfer",
        "medical_insurance": "Local Transfer",
        "residency": "Transfer",
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

# The Actions whose whole output is a Residency. Named because two code paths have to agree
# about it: the submit path, which opens the Residency through the extend branch in
# residency.py, and the path a row added after submit takes - which otherwise reads
# "not one of the new Actions, so open the four a renewal opens".
RESIDENCY_ONLY_ACTIONS = (EXTENSION_ACTION, VISA_EXTENSION_ACTION)

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


# WI-002096: the classification that puts a document inside the legal sequence. Kuwaiti
# permits and residency extensions are outside it - a Kuwaiti has no insurance, no residency
# and no civil ID process to follow the permit, and an extension is a single document on its
# own - so neither is gated and neither offers a next step.
SEQUENCED_CLASSIFICATIONS = {
    "Work Permit": ("work_permit_type", ("Renewal Expat", "Overseas", "Overseas (Government)", "Local Transfer")),
    "Medical Insurance": ("insurance_status", ("Renewal", "New", "Local Transfer")),
    "Residency": ("category", ("Renewal", "First Time", "Transfer")),
    "PACI": ("category", ("Renewal", "New Application", "Transfer")),
}

COMPLETED = "Completed"


def is_sequenced(doc):
    """Does this document sit inside the Work Permit -> ... -> PACI sequence (WI-002096)?"""
    classification = SEQUENCED_CLASSIFICATIONS.get(doc.doctype)
    if not classification:
        return False

    fieldname, values = classification
    return doc.get(fieldname) in values


def upstream_of(doc):
    """The document that legally has to be finished before this one (WI-002096)."""
    if doc.doctype not in SUB_DOCUMENT_SEQUENCE:
        return None

    position = SUB_DOCUMENT_SEQUENCE.index(doc.doctype)
    return SUB_DOCUMENT_SEQUENCE[position - 1] if position else None


def validate_sequence(doc, method=None):
    """Refuse to complete a step whose predecessor is not finished (WI-002096).

    Kuwait issues these in one order: the work permit, then the insurance it is a condition
    of, then the residency stamped against it, then the civil ID. Completing them out of
    order produces paperwork the ministry rejects, and the operator finds out weeks later.

    Only ever checks the step immediately before, because that step's own completion was
    gated the same way - so the whole chain is enforced without every document querying all
    of them.

    Scoped to documents opened by a Preparation. A permit or a residency raised on its own -
    a transfer paper, a cancellation - has no batch to be sequenced within, and there is
    nothing to look up.

    An upstream document that does not exist is not a blocker: the Action decides which
    documents a candidate gets, and a step that was never opened is not a step that is
    waiting.
    """
    if doc.get("workflow_state") != COMPLETED:
        return
    if not doc.get("preparation") or not doc.get("employee"):
        return
    if not is_sequenced(doc):
        return

    upstream = upstream_of(doc)
    if not upstream:
        return

    pending = frappe.get_all(
        upstream,
        filters={
            "preparation": doc.preparation,
            "employee": doc.employee,
            "docstatus": ["!=", 2],
            "workflow_state": ["!=", COMPLETED],
        },
        pluck="name",
        limit=1,
    )
    if not pending:
        return

    frappe.throw(
        _("{0} {1} has to be completed first.").format(
            _(upstream), frappe.bold(pending[0])
        ),
        title=_("Out of Sequence"),
    )


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


def sync_row_stages_into_doc(preparation):
    """Copy the stages just written to the database onto the in-memory rows.

    HD-1898774: `refresh_row_stage` writes with `db.set_value`, which is the right call -
    the row belongs to a submitted Preparation - but it writes past the document the
    request is holding. PRE-REN-2026-00010 opened all 48 of its documents and wrote the
    Ref DocType and Current Stage of all 12 rows, and the operator still saw six blank
    cells, because the document handed back to the browser was the one loaded before the
    run. Reading the three fields back onto the rows costs one query and makes the submit
    response say what the database says.

    Only the stage fields are touched, so nothing else about the in-memory document is
    disturbed and the form does not come back dirty.
    """
    rows = {row.name: row for row in preparation.preparation_record}
    if not rows:
        return

    written = frappe.get_all(
        "Preparation Record",
        filters={"name": ["in", list(rows)]},
        fields=["name", "ref_doctype", "ref_name", "ref_doctype_status"],
    )

    for record in written:
        row = rows.get(record.name)
        if not row:
            continue
        row.ref_doctype = record.ref_doctype
        row.ref_name = record.ref_name
        row.ref_doctype_status = record.ref_doctype_status


def notify_rows_refreshed(preparation_name):
    """Tell any browser holding this Preparation open that its rows have moved on.

    HD-1898774: the stages are written straight to the row and the parent's `modified` is
    deliberately left alone, so a client has nothing to notice - it keeps its copy in
    `locals` even when the operator routes away and back, and only a hard reload shows the
    values. Worse since the creation moved to a job: the stages now land minutes after the
    submit response rather than inside it. The form listens for this and reloads itself.
    """
    frappe.publish_realtime(
        DOCUMENTS_CREATED_EVENT,
        message={"preparation": preparation_name},
        doctype="Preparation",
        docname=preparation_name,
        after_commit=True,
    )


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

    def on_submit(self):
        self.validate_mandatory_fields_on_submit()
        validate_preparation_table(self)
        self.db_set('submitted_by', frappe.session.user)
        self.db_set('submitted_on', now_datetime())
        # The documents the rows owe are opened by a background job, not here: see
        # enqueue_document_creation. A row is still allowed to fail without taking the
        # batch down - the whole point of the per-row try - but a submit that came up
        # short no longer looks clean, because the job tells whoever submitted it.
        self.enqueue_document_creation()
        self.send_notifications()

    def enqueue_document_creation(self):
        """Open the documents this batch's rows owe, in the background when it is a batch.

        HD-1898774: PRE-ONB-2026-00008 submitted 27 Overseas rows, each opening six
        documents at about four seconds a row, and the web server killed the request at
        120 seconds part-way through row 24. The rows already done had each committed, so
        the batch survived three rows short with no Error Log and no message - the submit
        read as clean, and the gap only surfaced when an operator noticed three blank
        Current Stage cells and raised a ticket.

        A small batch is still opened inside the submit: ten rows is well inside the
        request timeout, and the operator gets the result - the documents on the form, the
        failures in a dialog - rather than having to come back to a notification for a
        handful of rows. Past that the work is queued, where it has no timeout over it and
        reports to whoever submitted.

        Either way the work itself is the same resumable call, so a batch that is cut off
        anyway can be finished with the button rather than by hand.
        """
        if len(self.preparation_record) <= INLINE_ROW_LIMIT:
            create_missing_documents(self.name)
            # create_missing_documents syncs the stages onto its own copy of the
            # Preparation, not this one, and this one is what the submit response hands
            # back to the browser (HD-1898774).
            sync_row_stages_into_doc(self)
            return

        frappe.enqueue(
            "one_fm.grd.doctype.preparation.preparation.create_missing_documents",
            queue="long",
            timeout=CREATION_JOB_TIMEOUT,
            enqueue_after_commit=True,
            job_id=f"create_missing_documents::{self.name}",
            deduplicate=True,
            now=bool(frappe.flags.in_test),
            preparation_name=self.name,
            notify_user=frappe.session.user,
        )

        frappe.msgprint(
            _("The documents for {0} rows are being created in the background. They will appear on this Preparation within a few minutes.").format(
                len(self.preparation_record)
            ),
            title=_("Creating Documents"),
            indicator="blue",
        )

    def recall_create_documents_for_new_actions(self):
        return create_documents_for_new_actions(self.name)

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
        return work_permit.create_work_permit_renewal(self.name)

    def recall_create_medical_insurance_renewal(self):
        return medical_insurance.valid_work_permit_exists(self.name)

    def recall_create_moi_renewal_and_extend(self):
        return residency.set_employee_list_for_moi(self.name)

    def recall_create_paci(self):
        return paci.create_PACI_renewal(self.name)

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


def create_documents_for_new_actions(preparation_name):
    """Generate the sub-documents the New Kuwaiti and Overseas Actions ask for (WI-001824).

    One row at a time, and one row's failure does not stop the rest: the same contract
    the renewal and extend paths already keep, so a single bad employee record cannot
    cost the whole batch its documents. The rows that failed are returned so the
    operator is told which ones, rather than the batch reading as a clean submit.
    """
    failures = []
    preparation = frappe.get_doc('Preparation', preparation_name)

    for row in preparation.preparation_record:
        if row.renewal_or_extend not in NEW_ACTION_DOCUMENTS:
            continue
        try:
            create_documents_for_row(row, preparation_name)
        except Exception as e:
            frappe.log_error(
                title=f"Error creating GRD documents for {row.employee} in Preparation {preparation_name}",
                message=frappe.get_traceback(),
            )
            failures.append({
                'employee': row.employee,
                'employee_name': row.full_name,
                'document': row.renewal_or_extend,
                'reason': str(e),
            })
            continue

    return failures


def report_document_creation_failures(failures, preparation=None, notify_user=None):
    """Tell the submitting operator which rows did not get their documents.

    Every creator keeps a per-row `try` so one bad employee record cannot cost the whole
    batch its documents, and each writes an Error Log. But an Error Log is not something
    the operator reads: PRE-REN-2026-00008 submitted 80 rows, opened 69 Work Permits and
    69 Medical Insurances instead of 70 each, and the gap only surfaced when someone
    noticed the connection badges did not agree. The submit still succeeds - a partial
    batch is the intended behaviour - but it no longer looks complete when it is not.

    Creation runs in a background job now (HD-1898774), where a msgprint reaches nobody:
    given the Preparation and the user who submitted it, the same table is delivered as a
    Notification Log instead. The msgprint is kept for the callers still running in a
    request.
    """
    if not failures:
        return

    rows = ""
    for failure in failures:
        rows += "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(
            escape_html(cstr(failure.get("employee"))),
            escape_html(cstr(failure.get("employee_name"))),
            escape_html(cstr(failure.get("document"))),
            escape_html(strip_html(cstr(failure.get("reason")))),
        )

    message = """
        <p>{intro}</p>
        <div class="table-responsive">
            <table class="table table-bordered table-sm small">
                <thead><tr><th>{employee}</th><th>{name}</th><th>{document}</th><th>{reason}</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <p class="text-muted small">{footer}</p>
    """.format(
        intro=_("This Preparation was submitted, but the following documents could not be created. Correct the cause and open them from the employee's record, or amend the row's Action."),
        employee=_("Employee"),
        name=_("Name"),
        document=_("Document"),
        reason=_("Reason"),
        rows=rows,
        footer=_("The full traceback for each is in the Error Log."),
    )

    title = _("Documents Not Created")

    if notify_user and preparation is not None:
        create_notification_log(
            "{0}: {1}".format(preparation.name, title), message, [notify_user], preparation
        )
        return

    frappe.msgprint(message, title=title, indicator="red", wide=True)


def create_documents_for_row(row, preparation_name):
    """Open the documents one Preparation row's Action calls for, in dependency order.

    The Work Permit comes first because Medical Insurance is opened against it - it
    reads the type, the application date and the passport expiry off the permit rather
    than being told them.

    Resumable (HD-1898774): a step whose document already exists against this
    Preparation and employee is skipped, so calling this a second time fills the gaps a
    first run left instead of opening a second set. PRE-ONB-2026-00008 submitted 27
    Overseas rows, the submit request was killed by the web server's 120-second timeout
    part-way through row 24, and the only way back was by hand - re-running anything
    would have duplicated the 23 complete rows.

    Raises on the first step that fails, which is the contract the per-row `try` in
    create_missing_documents is written against: a row whose Work Permit could not be
    opened has nothing for its Medical Insurance to be opened against either.
    """
    employee_doc = frappe.get_doc('Employee', row.employee)

    for step in missing_steps_for_row(row, preparation_name):
        _create_step(step, row, preparation_name, employee_doc)

    return _work_permit_of_row(preparation_name, row.employee)


def _create_step(step, row, preparation_name, employee_doc):
    """Open the one document a step stands for.

    The creator each step calls is the one that path has always used, and the arguments
    are the ones its own dispatcher passed: an Action in NEW_ACTION_DOCUMENTS states its
    classification in the plan, a renewal or an extension leaves the creator to derive it.
    """
    action = row.renewal_or_extend
    plan = NEW_ACTION_DOCUMENTS.get(action, {})

    if step == "work_permit":
        if action in NEW_ACTION_DOCUMENTS:
            return work_permit.create_wp_from_preparation(
                employee_doc, plan["work_permit"], preparation_name
            )
        return work_permit.create_wp_renewal(employee_doc, action, preparation_name)

    if step == "medical_insurance":
        work_permit_doc = _work_permit_of_row(preparation_name, row.employee)
        if not work_permit_doc:
            frappe.throw(
                _("No Work Permit for {0} on this Preparation to open the Medical Insurance against.").format(
                    row.employee
                )
            )
        return medical_insurance.create_mi_record(
            work_permit_doc, insurance_status=plan.get("medical_insurance")
        )

    if step == "residency":
        return residency.create_moi_record(
            employee_doc, action, preparation_name, category=plan.get("residency")
        )

    if step == "paci":
        # A renewal row's civil ID is opened as a Renewal, which is what create_PACI_renewal
        # passes; every Action with a plan states its own category.
        return paci.create_PACI(employee_doc, plan.get("paci") or "Renewal", preparation_name)

    if step == "medical_appointment":
        return medical_appointment.create_medical_appointment(
            employee_doc, plan["medical_appointment"], preparation_name
        )

    if step == "pcc_attestation":
        # Only the types that are missing: a run killed between the attestation and its
        # translation must not open the attestation a second time.
        return [
            pcc_attestation.create_pcc_attestation(
                employee_doc, plan["pcc_attestation"], preparation_name, attestation_type=attestation_type
            )
            for attestation_type in missing_pcc_types(row, preparation_name)
        ]


def expected_steps_for_row(row):
    """Which documents this row's Action is supposed to produce, in dependency order.

    One statement of what a row owes, read by the creator, by the resume and by the daily
    check. It mirrors the conditions the five creators on_submit used to call apply
    themselves - which is why the renewal branches below carry their nationality tests:
    Preparation's own dispatcher owns the Actions in ACTIONS_HANDLED_ON_SUBMIT, and
    Residency's "anything else is an extension" branch owns the rest.
    """
    action = row.get("renewal_or_extend")
    if not action:
        return []

    if action in NEW_ACTION_DOCUMENTS:
        plan = NEW_ACTION_DOCUMENTS[action]
        return [step for step in STEP_ORDER if step in plan]

    steps = set()
    if action in RENEWAL_ACTIONS:
        steps.add("work_permit")
    if action == RENEWAL_EXPAT and _nationality_of(row) != KUWAITI:
        steps.update(("medical_insurance", "residency", "paci"))
    if action not in ACTIONS_HANDLED_ON_SUBMIT and _nationality_of(row) != KUWAITI:
        steps.add("residency")

    return [step for step in STEP_ORDER if step in steps]


def missing_steps_for_row(row, preparation_name):
    """The expected steps this row has no document for yet.

    A document in any state counts, cancelled ones included: an operator who cancelled a
    Work Permit on purpose must not have a replacement opened behind them by the next
    resume or the daily check.
    """
    missing = []
    for step in expected_steps_for_row(row):
        if step == "pcc_attestation":
            if missing_pcc_types(row, preparation_name):
                missing.append(step)
            continue
        if not frappe.db.exists(
            STEP_DOCTYPES[step], {"preparation": preparation_name, "employee": row.employee}
        ):
            missing.append(step)

    return missing


def missing_pcc_types(row, preparation_name):
    """Which of the PCC records this row's nationality calls for are not open yet.

    An overseas hire always owes the attestation; a nationality whose Nationality
    Attestation Rule has Translation Required ticked owes a second record for the
    translation (WI-002104), and the two are counted separately.
    """
    rule = get_nationality_attestation_rule(_nationality_of(row))
    required = [pcc_attestation.ATTESTATION]
    if rule and rule.translation_required:
        required.append(pcc_attestation.TRANSLATION)

    return [
        attestation_type
        for attestation_type in required
        if not frappe.db.exists(
            "PCC Attestation",
            {
                "preparation": preparation_name,
                "employee": row.employee,
                "type": attestation_type,
            },
        )
    ]


def _work_permit_of_row(preparation_name, employee):
    """The Work Permit this Preparation opened for this employee, or None."""
    name = frappe.db.get_value(
        "Work Permit",
        {"preparation": preparation_name, "employee": employee},
        "name",
        order_by="creation desc",
    )
    return frappe.get_doc("Work Permit", name) if name else None


def _nationality_of(row):
    """The row's nationality, read off the Employee when the row has not fetched it."""
    return row.get("nationality") or frappe.db.get_value(
        "Employee", row.employee, "one_fm_nationality"
    )


def create_missing_documents(preparation_name, notify_user=None):
    """Open every document the rows of a submitted Preparation still owe.

    This is what submit queues (it is too slow to run in the request - 27 Overseas rows
    took over two minutes and the web server killed the request at 120 seconds, leaving
    three rows with no documents and nothing in the Error Log to say so), what the
    "Create Missing Documents" button runs, and what a second attempt after a failure
    runs. It is safe to run any number of times: a row with no gap is not touched.

    One row's failure does not stop the rest - the contract the per-row `try` has always
    kept - and the rows that failed are reported to the operator rather than only written
    to the Error Log.
    """
    preparation = frappe.get_doc("Preparation", preparation_name)
    failures = []

    for row in preparation.preparation_record:
        if not missing_steps_for_row(row, preparation_name):
            continue
        try:
            create_documents_for_row(row, preparation_name)
        except Exception as e:
            frappe.log_error(
                title=f"Error creating GRD documents for {row.employee} in Preparation {preparation_name}",
                message=frappe.get_traceback(),
            )
            failures.append({
                'employee': row.employee,
                'employee_name': row.full_name,
                'document': row.renewal_or_extend,
                'reason': str(e),
            })
            continue

    for row in preparation.preparation_record:
        refresh_row_stage(preparation_name, row.employee)

    # The stages are on the rows now, and nothing about that write reaches a browser on
    # its own (HD-1898774). Telling anyone holding the form open to reload is the only
    # route out of a job; the inline path additionally syncs its own document, which is
    # the one the submit response carries.
    notify_rows_refreshed(preparation_name)

    report_document_creation_failures(failures, preparation=preparation, notify_user=notify_user)

    return failures


def rows_missing_documents(preparation_name):
    """Every row of a Preparation that still owes a document, and which ones.

    Pure enough to feed three callers: the button's confirmation, the daily check's
    summary, and the tests.
    """
    preparation = frappe.get_doc("Preparation", preparation_name)

    gaps = []
    for row in preparation.preparation_record:
        missing = missing_steps_for_row(row, preparation_name)
        if missing:
            gaps.append({
                "employee": row.employee,
                "employee_name": row.full_name,
                "action": row.renewal_or_extend,
                "missing": [STEP_DOCTYPES[step] for step in missing],
            })

    return gaps


@frappe.whitelist()
def get_missing_document_summary(preparation: str):
    """How many rows of this Preparation still owe a document, for the form to show."""
    frappe.get_doc("Preparation", preparation).check_permission("read")

    gaps = rows_missing_documents(preparation)
    return {"count": len(gaps), "rows": gaps}


@frappe.whitelist(methods=["POST"])
def create_missing_documents_now(preparation: str):
    """Queue a resume for one Preparation, from the button on the form.

    Whoever can submit a Preparation can resume one: the documents are the ones their
    submit was supposed to open, and nothing else is created.
    """
    doc = frappe.get_doc("Preparation", preparation)
    doc.check_permission("submit")

    if doc.docstatus != 1:
        frappe.throw(_("Only a submitted Preparation can have its documents created."))

    gaps = rows_missing_documents(preparation)
    if not gaps:
        return {"queued": False, "count": 0}

    frappe.enqueue(
        "one_fm.grd.doctype.preparation.preparation.create_missing_documents",
        queue="long",
        timeout=CREATION_JOB_TIMEOUT,
        job_id=f"create_missing_documents::{preparation}",
        deduplicate=True,
        now=bool(frappe.flags.in_test),
        preparation_name=preparation,
        notify_user=frappe.session.user,
    )

    return {"queued": True, "count": len(gaps)}


def notify_preparations_with_missing_documents():
    """Daily: tell the GRD team about any submitted Preparation with documents missing.

    The safety net under the resume. A batch that lost its documents to a killed worker
    looks exactly like a complete one on the form - the Preparation is submitted, the rows
    carry their costing, and only the empty Current Stage on the last few rows says
    otherwise. PRE-ONB-2026-00008 went unnoticed until an operator happened to read the
    column and raised a ticket.

    It reports rather than creates: an operator who cancelled a document deliberately
    would otherwise have it reopened by a cron at midnight. The button next to the report
    is what creates them.
    """
    cutoff = add_days(nowdate(), -GAP_CHECK_WINDOW_DAYS)
    preparations = frappe.get_all(
        "Preparation",
        filters={"docstatus": 1, "posting_date": [">=", cutoff]},
        fields=["name", "grd_supervisor", "grd_operator", "submitted_by"],
        order_by="posting_date asc",
    )

    for preparation in preparations:
        try:
            gaps = rows_missing_documents(preparation.name)
        except Exception:
            frappe.log_error(
                title=f"Could not check {preparation.name} for missing GRD documents",
                message=frappe.get_traceback(),
            )
            continue

        if not gaps:
            continue

        recipients = {
            user
            for user in (
                preparation.grd_supervisor,
                preparation.grd_operator,
                preparation.submitted_by,
            )
            if user
        }
        if not recipients:
            continue

        doc = frappe.get_doc("Preparation", preparation.name)
        subject = _("{0}: {1} row(s) are missing their documents").format(
            preparation.name, len(gaps)
        )
        message = _missing_documents_message(doc, gaps)
        create_notification_log(subject, message, sorted(recipients), doc)


def _missing_documents_message(doc, gaps):
    """The table both the daily check and the failure report are read from."""
    rows = ""
    for gap in gaps:
        rows += "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(
            escape_html(cstr(gap.get("employee"))),
            escape_html(cstr(gap.get("employee_name"))),
            escape_html(cstr(gap.get("action"))),
            escape_html(", ".join(gap.get("missing") or [])),
        )

    return """
        <p>{intro}</p>
        <div class="table-responsive">
            <table class="table table-bordered table-sm small">
                <thead><tr><th>{employee}</th><th>{name}</th><th>{action}</th><th>{missing}</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <p><a href="{link}">{link_label}</a></p>
    """.format(
        intro=_("These rows of {0} have no document behind them. Open it and use <b>Create Missing Documents</b>.").format(
            escape_html(doc.name)
        ),
        employee=_("Employee"),
        name=_("Name"),
        action=_("Action"),
        missing=_("Missing"),
        rows=rows,
        link=get_url(doc.get_url()),
        link_label=doc.name,
    )


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

    # WI-002181: an extension opens a Residency and nothing else. The branch below reads as
    # "not one of the new Actions, so it is a renewal", which gave a row added after submit
    # a work permit, an insurance and a PACI that submitting the same row never would.
    if row.renewal_or_extend in RESIDENCY_ONLY_ACTIONS:
        try:
            residency.create_moi_record(
                frappe.get_doc("Employee", row.employee), row.renewal_or_extend, source
            )
        except Exception:
            frappe.log_error(
                title=f"Error creating Residency for {row.employee}",
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
        extension_type = "Renewal Expat"
    
    # The row's fees, not the master row's: a multi-year renewal pays the annual ones once
    # per year (WI-002092).
    return get_preparation_row_costing(extension_type, no_of_years), extension_type