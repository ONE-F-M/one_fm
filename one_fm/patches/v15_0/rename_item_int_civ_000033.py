import frappe

def execute():
    existing_item_name = "INT-CIV-000033"
    new_item_name = "INT-CIV-000002"
    if frappe.db.exists("Item", existing_item_name) and not frappe.db.exists("Item", new_item_name):
        frappe.rename_doc("Item", existing_item_name, new_item_name)
        frappe.db.set_value("Item", new_item_name, "item_code", new_item_name, update_modified=False)
        frappe.db.set_value("Item", new_item_name, "item_id", "000002", update_modified=False)