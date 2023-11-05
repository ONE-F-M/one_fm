import frappe


def execute():
    """"
        no_of_days_off in contract items is an integer field but NULL fills empty spots.
    """
    frappe.db.sql("""
        UPDATE `tabContract Item` SET no_of_days_off=0 WHERE no_of_days_off IS NULL;
    """)