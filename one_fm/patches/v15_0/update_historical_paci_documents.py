import frappe


def execute():
    frappe.db.sql("""
        UPDATE `tabPACI`
        SET workflow_state = 'Pending by GR Operator',
        paci_status = 'Under-Process'
        WHERE workflow_state = 'Apply Online by PRO'
    """)

    frappe.db.sql("""
        UPDATE `tabPACI`
        SET workflow_state = 'Draft',
        paci_status = 'Draft'
        WHERE workflow_state = 'Under Process'
    """)

    frappe.db.commit()
