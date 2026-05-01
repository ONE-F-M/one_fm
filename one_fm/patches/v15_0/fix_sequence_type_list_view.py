import frappe

def execute():
    # Force update
    frappe.db.sql(
        "UPDATE `tabDocField` SET in_list_view=1 "
        "WHERE parent='Agency Process Details' AND fieldname='sequence_type'"
    )
    frappe.db.commit()
