
import frappe
from frappe import _

def check_credit_limit(doc):
    '''Check if Sales Order grand_total exceeds customer credit limit'''

    if doc.docstatus != "1":
        return  # Only check submitted Sales Orders

    customer = frappe.get_doc("Customer", doc.customer)
    if not customer.credit_limit:
        return  # No credit limit set

    if doc.grand_total > customer.credit_limit:
        frappe.throw(_("Sales Order amount {0} exceeds credit limit {1} for customer {2}").format(
            doc.grand_total, customer.credit_limit, doc.customer))
