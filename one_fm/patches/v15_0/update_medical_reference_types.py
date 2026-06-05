# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# Patch: Update Agency Process Details to use new overseas medical DocTypes

import frappe


def execute():
    """Replace 'Medical Appointment' reference_type with the new dedicated DocTypes."""
    frappe.reload_doctype("Agency Process Details")
    frappe.reload_doctype("Candidate Country Process Details")
    # Update Medical Test rows → Overseas Medical Appointment WAFID
    apd = frappe.qb.DocType("Agency Process Details")
    frappe.qb.update(apd).set(
        apd.reference_type, "Overseas Medical Appointment WAFID"
    ).set(
        apd.reference_complete_status_field, "status"
    ).set(
        apd.reference_complete_status_value, "Fit"
    ).where(
        apd.process_name == "Medical Test"
    ).where(
        apd.reference_type == "Medical Appointment"
    ).run()

    # Update Remedical Test rows → Overseas Remedical
    frappe.qb.update(apd).set(
        apd.reference_type, "Overseas Remedical"
    ).set(
        apd.reference_complete_status_field, "status"
    ).set(
        apd.reference_complete_status_value, "Fit"
    ).where(
        apd.process_name == "Remedical Test"
    ).where(
        apd.reference_type == "Medical Appointment"
    ).run()

    # Also update any existing Candidate Country Process Details rows
    ccpd = frappe.qb.DocType("Candidate Country Process Details")
    frappe.qb.update(ccpd).set(
        ccpd.reference_type, "Overseas Medical Appointment WAFID"
    ).set(
        ccpd.reference_complete_status_field, "status"
    ).set(
        ccpd.reference_complete_status_value, "Fit"
    ).where(
        ccpd.process_name == "Medical Test"
    ).where(
        ccpd.reference_type == "Medical Appointment"
    ).run()

    frappe.qb.update(ccpd).set(
        ccpd.reference_type, "Overseas Remedical"
    ).set(
        ccpd.reference_complete_status_field, "status"
    ).set(
        ccpd.reference_complete_status_value, "Fit"
    ).where(
        ccpd.process_name == "Remedical Test"
    ).where(
        ccpd.reference_type == "Medical Appointment"
    ).run()

    frappe.db.commit()
