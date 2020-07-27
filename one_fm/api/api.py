import frappe
from frappe import _

@frappe.whitelist()
def _one_fm():
    print(frappe.local.lang)


