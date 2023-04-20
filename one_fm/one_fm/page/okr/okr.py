import frappe

@frappe.whitelist()
def get_profile():
    return frappe.get_doc("User", frappe.session.user)