# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# Patch: Update Agency Process Details to use new overseas medical DocTypes

import frappe


def execute():
    """Replace 'Medical Appointment' reference_type with the new dedicated DocTypes."""
    frappe.reload_doctype("Agency Process Details")
    frappe.reload_doctype("Candidate Country Process Details")
    # Update Medical Test rows → Overseas Medical Appointment WAFID
    frappe.db.sql("""
        UPDATE `tabAgency Process Details`
        SET reference_type = 'Overseas Medical Appointment WAFID',
            reference_complete_status_field = 'status',
            reference_complete_status_value = 'Fit'
        WHERE process_name = 'Medical Test'
          AND reference_type = 'Medical Appointment'
    """)

    # Update Remedical Test rows → Overseas Remedical
    frappe.db.sql("""
        UPDATE `tabAgency Process Details`
        SET reference_type = 'Overseas Remedical',
            reference_complete_status_field = 'status',
            reference_complete_status_value = 'Fit'
        WHERE process_name = 'Remedical Test'
          AND reference_type = 'Medical Appointment'
    """)

    # Also update any existing Candidate Country Process Details rows
    frappe.db.sql("""
        UPDATE `tabCandidate Country Process Details`
        SET reference_type = 'Overseas Medical Appointment WAFID',
            reference_complete_status_field = 'status',
            reference_complete_status_value = 'Fit'
        WHERE process_name = 'Medical Test'
          AND reference_type = 'Medical Appointment'
    """)

    frappe.db.sql("""
        UPDATE `tabCandidate Country Process Details`
        SET reference_type = 'Overseas Remedical',
            reference_complete_status_field = 'status',
            reference_complete_status_value = 'Fit'
        WHERE process_name = 'Remedical Test'
          AND reference_type = 'Medical Appointment'
    """)

    frappe.db.commit()
