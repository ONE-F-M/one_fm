import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-002025: the Embassy Cost Table, so a PCC Attestation can tell whether a candidate's
# country needs embassy attestation and what that embassy charges.
#
# The whole HR Settings set is re-run rather than the two new fields alone.
# create_custom_fields updates a field that already exists instead of duplicating it, so
# re-running is idempotent, and it repairs the insert_after chain in the same pass - the
# new section sits between the Renewal Extension Costing table and Costing Settings, so
# that section's anchor moved too.


def execute():
	frappe.reload_doc("grd", "doctype", "embassy_attestation_rate")
	create_custom_fields(get_hr_settings_custom_fields())
