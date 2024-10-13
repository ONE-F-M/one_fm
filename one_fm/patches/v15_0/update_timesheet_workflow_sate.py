import frappe


def execute():
    frappe.db.sql("""
        UPDATE
            `tabTimesheet`
        SET
            workflow_state = 'Pending Approval'
        WHERE
            workflow_state = 'Open'
    """)
