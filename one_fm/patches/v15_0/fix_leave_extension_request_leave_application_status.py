"""
Fix Leave Application status for leaves created via Leave Extension Request.

When Leave Extension Request creates leave applications programmatically,
it calls .insert() and .submit() directly, bypassing the workflow transition
that normally sets `status = 'Approved'`. This leaves the `status` field as
'Open' even though the document is submitted (docstatus=1) and
workflow_state='Approved'.

This patch updates all such affected Leave Applications.
"""
import frappe


def execute():
    # Fix all leave applications created via Leave Extension Request
    frappe.db.sql("""
        UPDATE `tabLeave Application`
        SET status = 'Approved'
        WHERE docstatus = 1
          AND workflow_state = 'Approved'
          AND status != 'Approved'
          AND custom_leave_extension_request IS NOT NULL
          AND custom_leave_extension_request != ''
    """)

    # Also fix these specific known affected leave applications
    specific_leaves = (
        'HR-LAP-2026-00686',
        'HR-LAP-2026-00710',
        'HR-LAP-2026-00729',
        'HR-LAP-2026-00797',
        'HR-LAP-2026-00798',
        'HR-LAP-2026-00799',
        'HR-LAP-2026-00800',
    )

    frappe.db.sql("""
        UPDATE `tabLeave Application`
        SET status = 'Approved'
        WHERE docstatus = 1
          AND workflow_state = 'Approved'
          AND status != 'Approved'
          AND name IN %s
    """, [specific_leaves])

    frappe.db.commit()
