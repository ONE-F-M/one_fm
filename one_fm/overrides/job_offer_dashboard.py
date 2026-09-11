"""WI-002426: the Visa Requests raised against a Job Offer, on the offer's Connections tab.

Job Offer belongs to hrms and ships no dashboard of its own, and the BA site records the
link as a DocType Link on the Job Offer record - which a custom app cannot add without
editing hrms. The hook is the supported way round that, and it gives the same thing: the
Visa Request entry, and the count beside it that Frappe keeps up to date as more requests
are raised against the same offer (AC 4 and AC 5).

Visa Request points at the offer through a field called `job_offer`, which is already the
fieldname Frappe derives from the parent doctype, so there is no non-standard fieldname to
declare.
"""

import frappe
from frappe import _

LINKED_DOCTYPE = "Visa Request"
GROUP_LABEL = "Visa"


def get_data(**kwargs):
	data = frappe._dict(kwargs.get("data") or {})
	transactions = data.setdefault("transactions", [])

	# Idempotent: get_dashboard_data() runs this on every form load, and a second entry
	# would show the Visa Request group twice.
	for group in transactions:
		if LINKED_DOCTYPE in (group.get("items") or []):
			return data

	transactions.append({"label": _(GROUP_LABEL), "items": [LINKED_DOCTYPE]})

	return data
