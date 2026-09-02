import frappe

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-002178: the Action is called "Renewal Expat" now, and the costing table it is
# configured in is called "HR Costing".
#
# The options on the Select fields come back with the doctype reload; what no reload
# covers is the value already stored on every row that carries the old spelling. A
# Select whose stored value is no longer one of its options is not just a wrong label -
# the next save of that document fails validation, so the rows are moved here.
#
# The Work Permit spelling was "Renewal Non Kuwaiti" rather than "Renewal (Non-Kuwaiti)";
# both become the one name.
RENAMES = (
	("GRD Renewal Extension Cost", "renewal_or_extend", "Renewal (Non-Kuwaiti)"),
	("Preparation Record", "renewal_or_extend", "Renewal (Non-Kuwaiti)"),
	# A Data mirror of the Action, not a Select - renamed so the two agree, and because
	# Residency's own reporting reads it.
	("Residency", "renewal_or_extend", "Renewal (Non-Kuwaiti)"),
	("Work Permit", "work_permit_type", "Renewal Non Kuwaiti"),
)

NEW = "Renewal Expat"


def execute():
	for module, doctype in (
		("grd", "grd_renewal_extension_cost"),
		("grd", "preparation_record"),
		("grd", "residency"),
		("grd", "work_permit"),
	):
		frappe.reload_doc(module, "doctype", doctype)

	# Re-run the whole HR Settings set: create_custom_fields updates a field that already
	# exists, so this renames the section and the table without touching anything else.
	create_custom_fields(get_hr_settings_custom_fields(), update=True)

	moved = {}
	for doctype, fieldname, old in RENAMES:
		moved[doctype] = frappe.db.count(doctype, {fieldname: old})
		if moved[doctype]:
			frappe.db.set_value(
				doctype, {fieldname: old}, fieldname, NEW, update_modified=False
			)

	verify(moved)


def verify(moved):
	"""A row left on the old value cannot be saved again, so the rename is checked."""
	for doctype, fieldname, old in RENAMES:
		left_behind = frappe.db.count(doctype, {fieldname: old})
		if left_behind:
			frappe.throw(
				f"WI-002178: {left_behind} {doctype} rows still carry {old!r}, which "
				f"{fieldname} no longer offers - they would fail validation on the next save."
			)

	label = frappe.db.get_value(
		"Custom Field", {"dt": "HR Settings", "fieldname": "renewal_extension_cost"}, "label"
	)
	if label != "HR Costing":
		frappe.throw(f"WI-002178: the HR Settings costing table is still labelled {label!r}.")

	print(f"WI-002178: renamed to {NEW!r} - " + ", ".join(f"{k}: {v}" for k, v in moved.items()))
