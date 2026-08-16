# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, add_days, get_url, date_diff, getdate
from frappe.model.document import Document
from frappe.utils import cstr, cint, get_fullname, flt
from frappe.utils import today, add_days, get_url
from datetime import date
from frappe.model.mapper import get_mapped_doc
from dateutil.relativedelta import relativedelta
from one_fm.api.notification import create_notification_log
from one_fm.processor import sendemail


def sendmail_reminder_to_book_appointment_for_pifss(): #before 1 week of the new month
    today = date.today()
    first_day = today.replace(day=1) + relativedelta(months=1)
    if date_diff(first_day,today) == 7: 
        operator = frappe.db.get_single_value('HR Settings', 'default_grd_operator_pifss')
        supervisor = frappe.db.get_single_value('HR Settings', 'default_grd_supervisor')
        if ('@' in operator):
            email_name = operator.split('@')[0]
        content = "<h4>Dear "+ email_name +",</h4><p>This month will end soon. Please make sure to book an apointment now for collecting PIFSS documents.</p>"       
        content = content
        sendemail(recipients=[operator],
            sender=supervisor,
            subject="Book Apointment For PIFSS", content=content, is_scheduler_email=True)

def sendmail_reminder_to_collect_pifss_documents(): # before 1 day of the new month
    today = date.today()
    first_day = today.replace(day=1) + relativedelta(months=1)
    if date_diff(first_day,today) == 1:
        operator = frappe.db.get_single_value('HR Settings', 'default_grd_operator')
        supervisor = frappe.db.get_single_value('HR Settings', 'default_grd_supervisor')
        if ('@' in operator):
            email_name = operator.split('@')[0]
        content = "<h4>Dear "+ email_name +",</h4><p> This email is reminder for you to collect PIFSS documents.</p>"       
        content = content
        sendemail(recipients=[operator],
            sender=supervisor,
            subject="Collect PIFSS Documents", content=content, is_scheduler_email=True)

@frappe.whitelist()
def mappe_to_work_permit_cancellation(source_name, target_doc=None):
    pifss_103_record = frappe.get_doc('PIFSS Form 103',source_name)
    print(pifss_103_record.employee)
    doc = get_mapped_doc("PIFSS Form 103", source_name, {
        "PIFSS Form 103": {
            "doctype": "Work Permit",
            "field_map": {
                "attach_end_of_service_from_pifss_website":"end_of_service_screenshot",
                "date_of_acceptance":"date_of_application",
                "work_permit_type":"work_permit_type",
                "employee":"employee"
            }
        }
    }, target_doc)
    return doc

@frappe.whitelist()
def mappe_to_work_permit_registration(source_name, target_doc=None):
    pifss_103_record = frappe.get_doc('PIFSS Form 103',source_name)
    print(pifss_103_record.employee)
    doc = get_mapped_doc("PIFSS Form 103", source_name, {
        "PIFSS Form 103": {
            "doctype": "Work Permit",
            "field_map": {
                "attach_registration_from_pifss_website":"registration_from_pifss_website",
                "date_of_acceptance":"date_of_application",
                "work_permit_type":"work_permit_type",
                "employee":"employee"
            }
        }
    }, target_doc)
    return doc

@frappe.whitelist()
def map_to_mgrp(source_name, target_doc=None):
    doc = get_mapped_doc("Work Permit", source_name, {
        "Work Permit": {
            "doctype": "MGRP",
            "field_map": {
                "work_permit_type":"work_permit_type",
                "employee":"employee",
                "first_name":"first_name",
                "civil_id":"civil_id",
                "last_name":"last_name",
                "employee_id":"employee_id",
                "end_of_service_date":"end_of_service_date",
            }
        }
    }, target_doc)
    return doc



def next_employee_document_idx(employee):
    """The idx a new Employee Document row should take.

    A raw insert does not get the ordering a child table append would, so it is worked
    out here rather than left at 0, where two rows would tie.
    """
    last = frappe.db.get_value(
        "Employee Document",
        {"parent": employee, "parenttype": "Employee"},
        "idx",
        order_by="idx desc",
    )
    return (last or 0) + 1


def attach_employee_document(employee, document_name, attach, valid_till, issued_on=None):
    """Record a government document on an Employee, without saving the whole Employee.

    ``employee.append(...)`` followed by ``employee.save()`` drags the entire Employee
    record through validation, so a GRD document could not be completed because of data
    that has nothing to do with it - 1,124 employees hold a Marital Status the field's
    options no longer accept ("Single", "Divorced", "Widowed"), and any full save of one
    throws. This writes the one row it actually has and nothing else.

    An existing row for the same ``document_name`` is updated rather than joined by a
    second one, so a renewal replaces what it renews instead of stacking up.
    """
    values = {
        "attach": attach,
        "issued_on": issued_on or today(),
        "valid_till": valid_till,
    }

    existing = frappe.db.exists(
        "Employee Document", {"parent": employee, "document_name": document_name}
    )
    if existing:
        frappe.db.set_value("Employee Document", existing, values)
        return existing

    row = frappe.get_doc({
        "doctype": "Employee Document",
        "parent": employee,
        "parenttype": "Employee",
        "parentfield": "one_fm_employee_documents",
        "idx": next_employee_document_idx(employee),
        "document_name": document_name,
        **values,
    })
    row.db_insert()
    return row.name


def set_renewal_extension_cost_totals(doc, method=None):
    """Sum each master fee row's components into its Total Amount (WI-002031).

    Runs on HR Settings validate. The sum was only ever done in the browser, so a row
    saved by any other route - a data import, a patch, the API - kept a Total Amount that
    did not match its own components, and every Preparation row that fetched it inherited
    the mismatch. The field is read-only, so nobody could correct it by hand either.

    Imported inside the function: the module is loaded by HR Settings' validate hook, and
    importing Preparation at module scope makes HR Settings depend on the GRD doctype
    module for a four-item tuple.
    """
    from one_fm.grd.doctype.preparation.preparation import COST_COMPONENT_FIELDS

    for row in doc.get('renewal_extension_cost') or []:
        row.total_amount = sum(flt(row.get(field)) for field in COST_COMPONENT_FIELDS)


def validate_nationality_attestation_rules(doc, method=None):
    """One row per nationality in the attestation rules table (WI-002025).

    The table is the master list of what a PCC needs for each nationality: whether the
    embassy attests and at what fee, whether MOFA attests and at what fee, and whether the
    certificate has to be translated. A nationality listed twice makes every one of those
    answers ambiguous, and the lookup would silently take whichever row came first - so an
    operator correcting a fee by adding a second row would see neither a change nor an error.
    """
    seen = set()
    for row in doc.get('nationality_attestation_rules') or []:
        if not row.nationality:
            continue
        if row.nationality in seen:
            frappe.throw(
                _("{0} appears more than once in the Nationality Attestation Rules. "
                  "Each nationality can only appear once.").format(frappe.bold(row.nationality)),
                title=_("Duplicate Nationality")
            )
        seen.add(row.nationality)


def get_nationality_attestation_rule(nationality):
    """The attestation rule configured for a nationality, or None if it has no row.

    Keyed on Nationality, matched against the candidate's own Employee.one_fm_nationality.
    The reporter's master data is a list of nationalities - "Nepali", "Sudanese",
    "Bangladeshi" - not of countries, so Nationality is the only field those values can be
    matched against. WI-002025's own wording says "Country (== Place of Birth)", but its
    example value is "Nepal" against real data that reads "Nepali", and WI-002028 and
    WI-002029 both word the rule as the candidate's nationality. Nationality is what the
    data supports.

    A nationality with no row needs nothing: no embassy, no MOFA, no translation. That is a
    meaningful answer rather than missing configuration, which is why the caller gets None
    and decides, instead of being handed a row of zeroes it cannot distinguish from a
    nationality that is configured to need nothing.

    Read off the cached HR Settings - it is a settings document read once per PCC save.
    """
    if not nationality:
        return None

    for row in frappe.get_cached_doc('HR Settings').get('nationality_attestation_rules') or []:
        if row.nationality == nationality:
            return row

    return None


def get_pcc_attestation_fees(nationality):
    """What a PCC for this nationality requires, and what each step costs.

    Returned as a dict of the three requirements and the three fees, so the PCC controller
    and the workflow conditions both read the same answer rather than each re-deriving it
    from the table.

    A step that is not required carries a fee of 0 rather than None: the fee fields on PCC
    Attestation are Currency and the cost breakdown adds them up, so a step that does not
    apply has to contribute nothing rather than blank out the total.

    A required MOFA step with no fee of its own falls back to the standard MOFA Fee in HR
    Settings. The reporter's data charges every nationality the same 5 KWD, so the per-row
    fee exists for the day one of them differs, and leaving it blank should mean "the usual"
    rather than "free".
    """
    settings = frappe.get_cached_doc('HR Settings')
    rule = get_nationality_attestation_rule(nationality)

    if not rule:
        return frappe._dict(
            embassy_required=False, embassy_fee=0.0,
            mofa_required=False, mofa_fee=0.0,
            translation_required=False, translation_fee=0.0,
        )

    return frappe._dict(
        embassy_required=bool(rule.embassy_required),
        embassy_fee=flt(rule.embassy_fee_kwd) if rule.embassy_required else 0.0,
        mofa_required=bool(rule.mofa_required),
        mofa_fee=(
            flt(rule.mofa_fee_kwd) or flt(settings.get('mofa_fee_kwd'))
        ) if rule.mofa_required else 0.0,
        translation_required=bool(rule.translation_required),
        translation_fee=flt(settings.get('pcc_translation_fee_kwd')) if rule.translation_required else 0.0,
    )
