import frappe
from frappe.model.utils.rename_field import rename_field

DOCTYPE = "Penalty And Investigation"

# old fieldname -> new fieldname, from the BA's layout (WI-001796).
RENAMES = (
	("location", "operations_site"),
	("deduction_type", "action_type"),
	("issuance_status", "employee_response"),
	("employee_rejection_remarks", "employee_remarks"),
	("legal_findings", "legal_department_remarks"),
)


def execute():
	"""Carry the penalty's data onto the renamed fields (WI-001796).

	Runs after the model sync, which is the only order that works: rename_field copies
	one column into another, so both have to exist. Frappe never drops the column of a
	removed field - there is no DROP COLUMN anywhere in its schema layer - so after the
	sync the old column is still there, holding its data, alongside the new empty one.

	Only `location` carries anything on production - all 325 records - but the others
	are renamed too so that a site which did fill them does not lose them either.
	"""
	frappe.reload_doc("legal", "doctype", "penalty_and_investigation")

	for old, new in RENAMES:
		if not frappe.db.has_column(DOCTYPE, old):
			continue
		# rename_field itself skips a missing target and says so; this keeps the log
		# readable when a site never had the old column at all.
		rename_field(DOCTYPE, old, new)

	# Created By is the visible copy of the raiser the layout adds. Frappe has recorded
	# them in `owner` all along, so backfill from there rather than leaving it blank.
	frappe.db.sql(
		f"""
		update `tab{DOCTYPE}`
		set created_by = owner
		where ifnull(created_by, '') = '' and ifnull(owner, '') != ''
		"""
	)

	frappe.db.commit()

	filled = frappe.db.count(DOCTYPE, {"operations_site": ["is", "set"]})
	total = frappe.db.count(DOCTYPE)
	print(f"WI-001796: {filled} of {total} penalties carry an Operations Site after the rename")
