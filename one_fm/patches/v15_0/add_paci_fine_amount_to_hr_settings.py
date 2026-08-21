from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-002023: the master PACI late fine, so the operator states whether the fine applies
# and the amount follows from one place.
#
# The whole HR Settings set is re-run rather than the one new field alone.
# create_custom_fields updates a field that already exists instead of duplicating it, so
# re-running the set is idempotent, and it repairs the insert_after chain in the same
# pass - the new field sits between "Days Before Expiry to Notify Supervisor" and the
# Renewal Extension Costing section, so that section's anchor moved too.


def execute():
	create_custom_fields(get_hr_settings_custom_fields())
