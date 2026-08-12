# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, add_days, get_url, date_diff, getdate
from frappe.model.document import Document
from frappe.utils import cstr, cint, get_fullname
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
