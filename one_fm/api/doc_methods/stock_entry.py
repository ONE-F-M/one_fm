import frappe
from frappe import _
from erpnext.accounts.doctype.budget.budget import validate_expense_against_budget

def validate_budget(doc, method):
	if doc.docstatus == 1:
		for data in doc.get("items"):
			args = data.as_dict()
			args.update(
				{
					"doctype": doc.doctype,
					"company": doc.company,
					"posting_date": doc.posting_date
				}
			)

			validate_expense_against_budget(args)
