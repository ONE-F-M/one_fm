import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-002016: the Penalty Email Recipients table, so the monthly penalty report knows who to
# send to and who to copy.
#
# The whole HR Settings set is re-run rather than the two new fields alone.
# create_custom_fields updates a field that already exists instead of duplicating it, so
# re-running is idempotent, and it repairs the insert_after chain in the same pass - the new
# section sits between Costing Settings and the Onboarding tab, so that tab's anchor moved.


def execute():
	frappe.reload_doc("legal", "doctype", "penalty_email_recipient")
	create_custom_fields(get_hr_settings_custom_fields())
	frappe.clear_cache(doctype="HR Settings")
