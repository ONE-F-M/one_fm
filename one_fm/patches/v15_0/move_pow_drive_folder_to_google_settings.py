import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.google_settings import get_google_settings_custom_fields

# WI-001981: the folder the Proof of Work export uploads into belongs on Google Settings,
# which is where the work item puts it. It was first built on ONEFM General Setting,
# beside the service account the upload authenticates with.
FIELDNAME = "pow_drive_folder_link"
OLD_DOCTYPE = "ONEFM General Setting"
NEW_DOCTYPE = "Google Settings"


def execute():
	create_custom_fields(get_google_settings_custom_fields())
	carry_over_the_configured_folder()


def carry_over_the_configured_folder():
	"""Move a folder already configured on the old page rather than asking for it again.

	Only when the new field is still empty, so a value set on Google Settings is never
	overwritten by a stale one left behind on the old page.
	"""
	# Read straight out of Singles rather than through get_single_value. By the time this
	# runs the field is gone from ONEFM General Setting's meta, and both of the obvious
	# readers fail on that: has_column raises TableMissingError (a Single has no table of
	# its own) and get_single_value raises "Field ... does not exist". The stored row
	# outlives the field, which is exactly what makes the value recoverable.
	# order_by=None because tabSingles has no `modified` column for the default ordering
	# to sort on - with it, this reads as "Unknown column 'modified' in 'ORDER BY'".
	existing = frappe.db.get_value(
		"Singles", {"doctype": OLD_DOCTYPE, "field": FIELDNAME}, "value", order_by=None
	)
	if not existing:
		return

	if frappe.db.get_single_value(NEW_DOCTYPE, FIELDNAME):
		return

	frappe.db.set_single_value(NEW_DOCTYPE, FIELDNAME, existing)
	print(f"WI-001981: carried the Proof of Work Drive folder over to {NEW_DOCTYPE}")
