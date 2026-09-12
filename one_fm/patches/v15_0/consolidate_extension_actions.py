import frappe

# WI-002179: "Extend 1 month", "Extend 2 months" and "Extend 3 months" were three Actions,
# three master fee rows and three ways of saying the same thing. There is one "Extension"
# Action now, and the duration is a number on the Preparation row.
#
# The Action is a Select, so a row left on a spelling the field no longer offers fails
# validation on its next save. Every stored row is moved here, and the duration it was
# carrying in its name is written to No. of Months so nothing is lost in the move.
MONTHS_BY_ACTION = {
	"Extend 1 month": "1 Month",
	"Extend 2 months": "2 Months",
	"Extend 3 months": "3 Months",
}

EXTENSION = "Extension"

# The costing table is read from HR Settings and nowhere else (`_master_fee_rows` filters
# on this parent). A superseded "GRD Settings" Single still holds the rows it was copied
# from when update_hr_settings_with_grd_settings moved them - a dead copy that nothing
# reads and that no form can save, so it is neither migrated nor counted here.
COSTING_PARENT = {"parent": "HR Settings", "parenttype": "HR Settings"}

# The master row that holds the monthly rate. The other two hold two and three times it,
# which is what the Preparation row multiplies out now - keeping them would double-count.
MONTHLY_MASTER_ROW = "Extend 1 month"


def execute():
	frappe.reload_doc("grd", "doctype", "grd_renewal_extension_cost")
	frappe.reload_doc("grd", "doctype", "preparation_record")

	moved = move_preparation_rows()
	kept = collapse_master_rows()
	renumber_costing_rows()

	verify(moved, kept)


def move_preparation_rows():
	"""Every Preparation row keeps the duration its old Action name spelled out."""
	moved = 0
	for action, months in MONTHS_BY_ACTION.items():
		rows = frappe.get_all("Preparation Record", filters={"renewal_or_extend": action}, pluck="name")
		for name in rows:
			frappe.db.set_value(
				"Preparation Record", name,
				{"renewal_or_extend": EXTENSION, "no_of_months": months},
				update_modified=False,
			)
		moved += len(rows)

	return moved


def collapse_master_rows():
	"""Three master fee rows become the one that states the monthly rate."""
	settings = frappe.get_doc("HR Settings")
	extend_rows = [
		row for row in settings.renewal_extension_cost
		if row.renewal_or_extend in MONTHS_BY_ACTION
	]
	if not extend_rows:
		return None

	# Sorted so the one-month row is first whatever order the table is in.
	extend_rows.sort(key=lambda row: row.renewal_or_extend != MONTHLY_MASTER_ROW)
	keeper = extend_rows[0]

	if keeper.renewal_or_extend != MONTHLY_MASTER_ROW:
		print(
			f"WI-002179: HR Settings had no {MONTHLY_MASTER_ROW!r} row, so "
			f"{keeper.renewal_or_extend!r} became the Extension row. Its amounts are for that "
			"many months, not for one - HR has to restate them as a monthly rate."
		)

	keeper.renewal_or_extend = EXTENSION
	for row in extend_rows[1:]:
		# Document.remove, not the list's: the list's takes the row out and leaves every
		# survivor's idx where it was. Nothing else renumbers - a save keeps the idx each
		# row already carries, and _init_child only numbers a row that has none.
		settings.remove(row)

	settings.flags.ignore_mandatory = True
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.clear_cache(doctype="HR Settings")

	return keeper.total_amount


def costing_rows():
	return frappe.get_all(
		"GRD Renewal Extension Cost",
		filters=COSTING_PARENT,
		fields=["name", "idx"],
		order_by="idx asc, creation asc",
	)


def renumber_costing_rows():
	"""Close the gap this patch left on the sites it has already run on.

	It cannot live in collapse_master_rows: that returns early once the extend rows are
	gone, so on a re-run it would never be reached. Add Row numbers a new row by the
	table's length rather than by its highest idx (create_new.js, and _init_child server
	side), so a gap in the middle means the next row HR adds collides with an existing one
	and the table's order stops being decidable.
	"""
	renumbered = False
	for position, row in enumerate(costing_rows(), start=1):
		if row.idx != position:
			frappe.db.set_value(
				"GRD Renewal Extension Cost", row.name, "idx", position, update_modified=False
			)
			renumbered = True

	if renumbered:
		frappe.clear_cache(doctype="HR Settings")


def verify(moved, kept):
	"""A row left on a removed option cannot be saved again, so the move is checked."""
	for action in MONTHS_BY_ACTION:
		for doctype, filters in (
			("Preparation Record", {}),
			("GRD Renewal Extension Cost", COSTING_PARENT),
		):
			left_behind = frappe.db.count(doctype, dict(filters, renewal_or_extend=action))
			if left_behind:
				frappe.throw(
					f"WI-002179: {left_behind} {doctype} rows still carry {action!r}, which "
					"renewal_or_extend no longer offers - they would fail validation on the "
					"next save."
				)

	numbering = [row.idx for row in costing_rows()]
	if numbering != list(range(1, len(numbering) + 1)):
		frappe.throw(
			f"WI-002179: HR Costing is numbered {numbering}, not 1 to {len(numbering)} - "
			"Add Row numbers a new row by count, so a gap makes it collide with a row that "
			"is already there."
		)

	print(
		f"WI-002179: moved {moved} Preparation rows to {EXTENSION!r}; master row total "
		f"{kept if kept is not None else 'already collapsed'}"
	)
