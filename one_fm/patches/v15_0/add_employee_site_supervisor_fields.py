import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.employee import get_employee_custom_fields

FIELDNAME = "custom_site_supervisor_user"


def execute():
	"""Add Site Supervisor User to Employee and backfill it (WI-001780).

	One field, not the two the BA site carries: `tabEmployee` sits at MariaDB's
	65,535-byte row limit and has room for exactly one more varchar(140). Adding a
	second fails with "Row size too large", and an ALTER that fails leaves the Custom
	Field record behind without its column, which breaks every Employee write - so
	the field count here is deliberate, not an omission.
	"""
	field = next(
		(
			f
			for f in get_employee_custom_fields()["Employee"]
			if f["fieldname"] == FIELDNAME
		),
		None,
	)
	if not field:
		frappe.throw(f"{FIELDNAME} is missing from one_fm's Employee custom fields.")

	create_custom_fields({"Employee": [field]})

	if not frappe.db.has_column("Employee", FIELDNAME):
		# The column could not be added, so the Custom Field is an orphan: Frappe
		# builds its INSERT/UPDATE from meta, so leaving it would break every
		# Employee save. Remove it and fail loudly instead.
		orphan = frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": FIELDNAME})
		if orphan:
			frappe.delete_doc("Custom Field", orphan, force=True, ignore_permissions=True)
		frappe.clear_cache(doctype="Employee")
		frappe.throw(
			f"Could not add the {FIELDNAME} column to tabEmployee (row size limit). "
			"The Custom Field has been removed so Employee saves keep working."
		)

	backfill()


def backfill():
	"""Fill the field for existing employees.

	It is set on save, so without this every employee would read empty until someone
	touched the record. Grouped by site: one write per employee, but the supervisor
	chain is resolved once per site rather than once per employee.
	"""
	from one_fm.overrides.employee import get_site_supervisor_user

	sites = frappe.get_all(
		"Employee",
		filters={"site": ["is", "set"]},
		distinct=True,
		pluck="site",
	)

	updated = 0
	for site in sites:
		user = get_site_supervisor_user(site)
		if not user:
			continue
		names = frappe.get_all("Employee", filters={"site": site}, pluck="name")
		for name in names:
			frappe.db.set_value(
				"Employee", name, FIELDNAME, user, update_modified=False
			)
		updated += len(names)

	frappe.db.commit()
	print(f"WI-001780: backfilled {FIELDNAME} on {updated} employee(s) across {len(sites)} site(s)")
