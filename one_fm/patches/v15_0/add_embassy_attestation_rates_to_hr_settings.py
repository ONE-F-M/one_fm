import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-002025: the Nationality Attestation Rules master, so a PCC Attestation can tell what
# each nationality needs - embassy, MOFA, translation - and what each step costs.
#
# The whole HR Settings set is re-run rather than the new fields alone. create_custom_fields
# updates a field that already exists instead of duplicating it, so re-running is
# idempotent, and it repairs the insert_after chain in the same pass - the new section sits
# between the Renewal Extension Costing table and Costing Settings, so that section's anchor
# moved too.
#
# The earlier shape of this feature keyed the table on Country and held only an embassy fee.
# It was never released, so its Custom Field and its child rows are dropped rather than
# migrated: there is nothing in them to preserve, and leaving a Table field pointing at a
# deleted doctype breaks every HR Settings save.
SUPERSEDED_FIELDS = ("embassy_attestation_rates", "embassy_attestation_rates_section")


def execute():
	for fieldname in SUPERSEDED_FIELDS:
		frappe.db.delete("Custom Field", {"dt": "HR Settings", "fieldname": fieldname})

	if frappe.db.exists("DocType", "Embassy Attestation Rate"):
		frappe.delete_doc("DocType", "Embassy Attestation Rate", force=True, ignore_missing=True)

	frappe.reload_doc("grd", "doctype", "nationality_attestation_rule")
	create_custom_fields(get_hr_settings_custom_fields())
	frappe.clear_cache(doctype="HR Settings")
