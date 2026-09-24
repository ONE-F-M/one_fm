"""WI-002883: give the accommodations that predate the Status field a status.

The field is mandatory, as the business analyst's copy has it. Mandatory bites on save, so
without this the eight accommodations already on the site could not be saved again until
somebody opened each one and picked a value - a field added to describe them would have
stopped them being edited at all.

Active, because that is what they are: every one of them is an accommodation the site is
using today. The alternative - leaving them blank and letting the operator choose - is the
same choice made eight times over, and it is made here once so nothing is stranded in the
meantime.
"""

import frappe

DOCTYPE = "Accommodation"
DEFAULT_STATUS = "Active"


def execute():
	if not frappe.db.has_column(DOCTYPE, "status"):
		# The column arrives with the DocType on migrate. Nothing to fill in yet.
		return

	# update_modified=False: nobody edited these accommodations, a field was added to them.
	frappe.db.set_value(
		DOCTYPE, {"status": ["in", [None, ""]]}, "status", DEFAULT_STATUS, update_modified=False
	)

	blank = frappe.db.count(DOCTYPE, {"status": ["in", [None, ""]]})
	if blank:
		frappe.throw(
			f"WI-002883: {blank} {DOCTYPE} records still have no status, so they cannot be "
			"saved while the field is mandatory."
		)
