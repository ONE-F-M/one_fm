import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.shift_request import get_shift_request_custom_fields

# WI-001834: the Shift Preview grid an approver reads before approving a multi-day request.
# create_custom_fields is idempotent, so the whole Shift Request set is handed to it rather
# than the two new rows being singled out - that also repairs any of the others a previous
# install missed.
FIELDS = ("custom_section_break_z4s37", "custom_shift_preview")


def execute():
	create_custom_fields(get_shift_request_custom_fields())

	missing = [
		fieldname
		for fieldname in FIELDS
		if not frappe.db.exists("Custom Field", {"dt": "Shift Request", "fieldname": fieldname})
	]
	if missing:
		frappe.throw(f"WI-001834: Shift Request is still missing {missing}")

	frappe.clear_cache(doctype="Shift Request")
