import frappe


def after_insert(doc, event):
    """
    :param doc:
    :param event:
    :return:
    """
    if not doc.role_profile_name == "Only Employee":
        if frappe.db.exists({"doctype":"Employee", "user_id":doc.name}):
            doc.db_set("role_profile_name", "Only Employee")

