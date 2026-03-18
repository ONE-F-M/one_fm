import frappe
from frappe import _

def check_credit_limit(doc, method=None):
    """
    Check if the customer's credit limit is exceeded by the current Sales Order's grand total.
    """
    if not doc.customer:
        return

    # Fetch customer's credit limit for the current company
    # Credit limit is usually defined per customer per company in Customer Credit Limit child table
    credit_limit = frappe.db.get_value("Customer Credit Limit", 
        {"parent": doc.customer, "parenttype": "Customer", "company": doc.company}, 
        "credit_limit")
    
    if credit_limit and doc.grand_total > credit_limit:
        frappe.throw(
            _("Sales Order grand total {0} exceeds the customer's credit limit of {1}").format(
                doc.grand_total, credit_limit
            )
        )
