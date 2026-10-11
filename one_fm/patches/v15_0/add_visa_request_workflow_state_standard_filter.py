"""Make Workflow State a standard filter on the Visa Request list view.

workflow_state on Visa Request is the Custom Field "Visa Request-workflow_state", created
when the Workflow is saved - it is not on the DocType JSON. A Property Setter is used so the
flag survives the Workflow being re-saved.
"""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

CUSTOM_FIELD = "Visa Request-workflow_state"


def execute():
	# The Custom Field arrives with the Workflow; on a site that does not have it yet there
	# is nothing to flag, and a Property Setter for a missing field is just noise.
	if not frappe.db.exists("Custom Field", CUSTOM_FIELD):
		return

	make_property_setter(
		"Visa Request",
		"workflow_state",
		"in_standard_filter",
		1,
		"Check",
	)
