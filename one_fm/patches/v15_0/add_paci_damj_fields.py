import frappe

# WI-002109: PACI carries the Damj merge details now - the civil ID the employee held before
# and the government letter authorising the merge - and the fine amount and the rejection
# block only show when they apply.
FIELDS = ("damj_is_applicable", "original_civil_id", "upload_damj_letter", "upload_damj_letter_on")


def execute():
	frappe.reload_doc("grd", "doctype", "paci")

	verify()


def verify():
	meta = frappe.get_meta("PACI")
	missing = [fieldname for fieldname in FIELDS if not meta.get_field(fieldname)]
	if missing:
		frappe.throw(f"WI-002109: {missing} were not added to PACI.")
