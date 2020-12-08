import frappe

@frappe.whitelist(allow_guest=True)
def get_nationality_list():
    return frappe.get_all('Nationality')
