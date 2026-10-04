# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-002593: what a Work Permit or a PACI is called before its Civil ID exists.

Both were titled by `civil_id`, which is exactly the field an onboarding candidate has not
got yet - the Work Permit is one of the steps that produces it. So every record opened for
a new joiner was titled by nothing at all, in the list, in every Link field and on every
dashboard badge, until somebody typed the Civil ID in.

The title falls back through what the record does know, and comes back to the Civil ID the
moment it is issued. It is not a field anybody types: it is derived on every save.
"""

# In order. The Civil ID is the identifier these documents are filed under, so it wins
# whenever it is there; the Employee ID is what the candidate is called in the meantime;
# the Employee link is the last resort for a record whose employee_id has not been
# fetched yet. The employee name is deliberately not among them: PACI has no field for
# it, so a shared list naming it would read blank on half the records it is meant to
# title.
TITLE_SOURCES = ("civil_id", "employee_id", "employee")


def document_title(doc) -> str:
	"""The first identifier this document actually carries."""
	for fieldname in TITLE_SOURCES:
		value = (doc.get(fieldname) or "").strip()
		if value:
			return value
	return ""


def set_document_title(doc) -> None:
	"""Derive the title on save.

	Called from the controller rather than left to a fetch_from, because a fetch only
	copies one field and this has to choose between three - and has to change its mind
	when the Civil ID arrives.
	"""
	doc.title = document_title(doc)
