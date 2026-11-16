import frappe

SOURCE_DOCTYPE = "Project Manpower Request"
TARGET_DOCTYPE = "Manpower Request Reason"
FIELDNAME = "reason"

# The Reason select options as the field held them on 2026-11-16, immediately before
# the conversion to a Link. Only used when the options can no longer be read off the
# field, which is the case on any site where the fieldtype was already changed by
# hand before this patch ran. Keeping them here is what stops such a site from
# seeding only the reasons that happen to be in use: "High Salary" and "Annual Leave
# Reliever" are valid options with no request against them.
SELECT_OPTIONS_BEFORE_CONVERSION = [
	"Exit",
	"New Project",
	"High Salary",
	"Overtime",
	"Shortage",
	"Sub Contractor",
	"Day OFF Reliever",
	"Annual Leave Reliever",
	"Replacement",
]


def execute():
	"""HD-1927006: seed Manpower Request Reason from the Reason select options.

	Operations asked for the Reason options on Project Manpower Request to become
	records they can maintain themselves, so Reason turns from a Select into a Link
	to the new single field "Manpower Request Reason" doctype. The select options are
	the list to start from: they are what the business already agreed on, and the
	1,103 existing requests all hold one of those strings. Seeding anything else
	would leave saved requests pointing at a reason that has no record, which a Link
	field renders as a broken value the next save writes back empty.

	This is a pre_model_sync patch on purpose. Model sync is what rewrites the field
	from Select to Link, and with it the options property: once sync has run, the
	newline separated list is gone and replaced by the target doctype name. Running
	before sync is the only point where the options can still be read off the field
	itself, which is why the list copied into this file is a fallback for sites that
	converted the field by hand and never the first source.

	Running before sync also means the target table does not exist yet, so the
	doctype is reloaded from its JSON first. That is also what makes the patch safe
	on a site that has never seen the doctype.

	The stored values are folded in on top of the options. On a site that is behind
	on remap_removed_pmr_reasons, records may still hold a retired reason that the
	select no longer lists; those values get a record too, so no request is left with
	a Reason the Link cannot resolve. On this site that set is empty, since the remap
	already ran.

	Idempotent: a reason that already has a record is left alone, so a re-run adds
	nothing and overwrites nothing an HR Manager has since edited.
	"""
	frappe.reload_doc("one_fm", "doctype", frappe.scrub(TARGET_DOCTYPE))

	reasons = get_select_options() + get_stored_reasons()

	seen = set()
	for reason in reasons:
		if reason in seen:
			continue
		seen.add(reason)

		if frappe.db.exists(TARGET_DOCTYPE, reason):
			continue

		frappe.get_doc(
			{
				"doctype": TARGET_DOCTYPE,
				frappe.scrub(TARGET_DOCTYPE): reason,
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()


def get_select_options() -> list:
	"""The Reason options as the field still holds them, before model sync.

	Read from the DocField row rather than the meta so the target doctype name is
	never mistaken for an option once the field has been converted. If the field is
	no longer a Select, the options are already lost and the list captured above is
	used in their place.
	"""
	field = frappe.db.get_value(
		"DocField",
		{"parent": SOURCE_DOCTYPE, "fieldname": FIELDNAME},
		["fieldtype", "options"],
		as_dict=True,
	)

	if not field or field.fieldtype != "Select" or not field.options:
		return list(SELECT_OPTIONS_BEFORE_CONVERSION)

	return [option.strip() for option in field.options.split("\n") if option.strip()]


def get_stored_reasons() -> list:
	"""Every distinct Reason actually saved on a request, retired options included."""
	stored = frappe.get_all(SOURCE_DOCTYPE, pluck=FIELDNAME, distinct=True)

	return [reason.strip() for reason in stored if reason and reason.strip()]
