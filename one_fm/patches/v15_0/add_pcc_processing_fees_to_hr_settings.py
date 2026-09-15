from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-002026: the master MOFA and PCC translation rates, so a PCC Attestation fetches them
# rather than having them typed in per record.
#
# The whole HR Settings set is re-run rather than the new fields alone. create_custom_fields
# updates a field that already exists instead of duplicating it, so re-running is idempotent,
# and it repairs the insert_after chain in the same pass - the new fields sit between the
# Embassy Attestation Rates table and Costing Settings, so that section's anchor moved.


def execute():
	create_custom_fields(get_hr_settings_custom_fields())
