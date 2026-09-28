# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-002498: raising a Residency Payment Request from the record that owes the money.

A Preparation, a Residency fine and a PACI fine all end in a payment, and the only way to
raise one was to open Residency Payment Request and key the reference in by hand - which
is where the wrong document name and the wrong amount came from.

The button opens a Residency Payment Request already pointed at the record it was raised
from, with the reference rows filled in (WI-002499). Nothing is written here: the document
comes back unsaved and the operator saves it, which is what keeps a mistyped click from
leaving an empty payment request behind.

One request per record. Once a Draft or a Submitted one names this document, the button
opens that one instead of raising a second - two payment requests against one Residency
fine is the fine paid twice.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

# The three records that can owe a payment, and what has to be true of each before the
# button is worth showing. Kept here rather than in the three form scripts so the server
# refuses exactly what the forms decline to offer.
SOURCE_DOCTYPES = ("Preparation", "Residency", "PACI")

CANCELLED = "Cancelled"

# A request that is Draft or Submitted is a live claim on this document. A cancelled one
# is not, so a record whose only request was cancelled can raise another.
LIVE_DOCSTATUS = (0, 1)


def is_payable(doc) -> bool:
	"""Is there anything to raise a payment request for on this record?

	Preparation: the costing is what the document is for, and it is only real once it has
	been submitted.

	Residency and PACI: only the fine. The base processing amounts belong to the
	Preparation that opened them, and a fine that is ticked without an amount is a fine
	nobody has worked out yet.
	"""
	if doc.doctype == "Preparation":
		return doc.docstatus == 1

	if doc.get("workflow_state") == CANCELLED:
		return False

	if doc.doctype == "Residency":
		return bool(doc.get("residency_fine_to_be_added") and doc.get("residency_fine_amount_kwd"))

	if doc.doctype == "PACI":
		return bool(doc.get("is_paci_fine_applicable") and doc.get("paci_fine_amount_kwd"))

	return False


def existing_request(source_doctype: str, source_name: str):
	"""The live Residency Payment Request already naming this document, if there is one."""
	return frappe.db.get_value(
		"Residency Payment Request",
		{
			"reference_doctype": source_doctype,
			"reference_docname": source_name,
			"docstatus": ["in", LIVE_DOCSTATUS],
		},
		"name",
	)


@frappe.whitelist()
def make_residency_payment_request(source_doctype: str, source_name: str) -> dict:
	"""Open a Residency Payment Request for this record, or point at the one that exists.

	Returns either {"existing": name} or {"doc": <unsaved document>}; the form script
	routes to one or syncs the other.
	"""
	if source_doctype not in SOURCE_DOCTYPES:
		frappe.throw(
			_("A Residency Payment Request cannot be raised from {0}.").format(source_doctype)
		)

	source = frappe.get_doc(source_doctype, source_name)
	source.check_permission("read")
	frappe.has_permission("Residency Payment Request", "create", throw=True)

	if not is_payable(source):
		frappe.throw(
			_("{0} {1} has nothing to raise a payment request for.").format(
				_(source_doctype), source_name
			)
		)

	existing = existing_request(source_doctype, source_name)
	if existing:
		return {"existing": existing}

	request = frappe.new_doc("Residency Payment Request")
	request.posting_date = nowdate()
	request.company = default_company(source)
	request.reference_doctype = source_doctype
	request.reference_docname = source_name

	for row in reference_rows(source):
		request.append("references", row)

	return {"doc": request.as_dict()}


def default_company(source):
	"""The company the request is raised for.

	Taken from the source where it carries one and from the site's default otherwise,
	rather than named in code - a hard-coded company is one rename away from a payment
	request nobody can save.
	"""
	return (
		source.get("company")
		or frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)


# WI-002499: what a freshly opened reference row says about itself. Everything else on the
# row - supplier, payment request, payment entry, mode of payment, bank account, account,
# payment reference - is left blank on purpose: it is the finance user's to fill in when
# the payment is actually made, and a default there would read as a decision somebody took.
REFERENCE_DEFAULTS = {
	"reference_doc_status": "Submitted",
	"payment_status": "Initiated",
}


def reference_rows(source) -> list:
	"""One reference row per thing this record owes (WI-002499).

	`reference_name` is the SOURCE document, not the row - a Preparation with twelve
	employees produces twelve rows all naming the same Preparation, which is what makes the
	payment traceable back to the document that raised it.
	"""
	if source.doctype == "Preparation":
		# One row per employee on the costing. A row with nothing to pay is not a payment.
		return [
			_row(source, row.employee, row.total_amount)
			for row in source.get("preparation_record") or []
			if row.employee and flt(row.total_amount)
		]

	if source.doctype == "Residency":
		return [_row(source, source.employee, source.residency_fine_amount_kwd)]

	if source.doctype == "PACI":
		return [_row(source, source.employee, source.paci_fine_amount_kwd)]

	return []


def _row(source, employee, amount) -> dict:
	return {
		"employee": employee,
		"reference_type": source.doctype,
		"reference_name": source.name,
		"amount": flt(amount),
		**REFERENCE_DEFAULTS,
	}
