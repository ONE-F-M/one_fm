import frappe
from frappe import _

def check_credit_limit(doc, method=None):
    """
    Checks if the Sales Order's grand total exceeds the customer's credit limit.
    """
    customer = doc.customer
    company = doc.company

    credit_limit = frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": customer, "company": company},
        "credit_limit"
    ) or 0  # Default to 0 if no credit limit is set

    grand_total = doc.grand_total

    if grand_total > credit_limit:
        frappe.throw(
            _("Grand total exceeds the credit limit for customer {0}. Credit Limit: {1}, Grand Total: {2}").format(
                customer, credit_limit, grand_total
            )
        )
