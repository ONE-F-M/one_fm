import frappe
from frappe import _

def check_credit_limit(doc, method):
	if doc.customer:
		credit_limit = frappe.db.get_value("Customer", doc.customer, "credit_limit")
		if credit_limit and doc.grand_total > credit_limit:
			frappe.throw(
				_("Grand Total exceeds the customer's credit limit of {0}").format(credit_limit),
				frappe.ValidationError
			)
