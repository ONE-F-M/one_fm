import frappe

def execute():
    if frappe.db.exists("Item", "INT-CIV-000033") and not frappe.db.exists("Item", "INT-CIV-000002"):
        frappe.rename_doc("Item", "INT-CIV-000033", "INT-CIV-000002", ignore_permissions=True)
        frappe.db.set_value("Item", "INT-CIV-000002", "item_code", "INT-CIV-000002", update_modified=False)
        frappe.db.set_value("Item", "INT-CIV-000002", "item_id", "000002", update_modified=False)
