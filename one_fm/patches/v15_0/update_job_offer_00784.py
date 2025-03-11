import frappe

def execute():
    frappe.db.sql(
        """
            UPDATE `tabJob Offer`
            SET one_fm_erf = 'ERF-2024-00014'
            WHERE name = 'HR-OFF-2024-00784'
        """
    )