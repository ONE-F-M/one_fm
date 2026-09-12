"""WI-002426: the Visa Requests raised against a Job Offer, on the offer's Connections tab.

Job Offer belongs to hrms and ships no dashboard of its own, and the BA site records the
link as a DocType Link on the Job Offer record - which a custom app cannot add without
editing hrms. The hook is the supported way round that, and it has to supply what a real
DocType Link would have: the group, and the fieldname on the other side.

The fieldname is not optional. Meta.add_doctype_links() sets data.fieldname from
link_fieldname for real links, and the client reads it twice - get_document_filter() uses
it to open the list filtered to this offer, and set_open_count() returns early without it,
so the count beside the entry never loads. Declared here it was missing, which left the
entry opening the whole Visa Request list and showing no count at all.
"""

import frappe
from frappe import _

LINKED_DOCTYPE = "Visa Request"
LINK_FIELDNAME = "job_offer"
GROUP_LABEL = "Visa"


def get_data(**kwargs):
	data = frappe._dict(kwargs.get("data") or {})
	transactions = data.setdefault("transactions", [])
	data.setdefault("non_standard_fieldnames", {})
	data.setdefault("internal_links", {})

	# Idempotent: get_dashboard_data() runs this on every form load, and a second entry
	# would show the Visa Request group twice.
	if not any(LINKED_DOCTYPE in (group.get("items") or []) for group in transactions):
		transactions.append({"label": _(GROUP_LABEL), "items": [LINKED_DOCTYPE]})

	# The default for every entry the dashboard carries, and what set_open_count() needs
	# before it will fetch anything. Only set when nothing else has claimed it.
	if not data.get("fieldname"):
		data.fieldname = LINK_FIELDNAME

	# And the per-doctype answer, so this entry keeps filtering on job_offer even if
	# another app later adds a link whose own fieldname becomes the default.
	data.non_standard_fieldnames[LINKED_DOCTYPE] = LINK_FIELDNAME

	return data
