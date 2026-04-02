import frappe

def execute():
    """Sync item_type from Contract Item to Contract Items Operation"""
    frappe.db.sql("""
        UPDATE `tabContract Items Operation` ops
        JOIN `tabContract Item` ci ON ops.parent = ci.parent AND ops.item_code = ci.item_code
        SET ops.item_type = ci.item_type
        WHERE IFNULL(ops.item_type, '') = '' AND IFNULL(ci.item_type, '') != ''
    """)
    frappe.db.commit()
