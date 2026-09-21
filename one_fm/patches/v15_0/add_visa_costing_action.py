import frappe

# The HR Costing table gets a "Visa Costing" Action whose work permit fee is a flat 20 KWD.
#
# Not migrated from the BA site: that site has no Visa Costing row, and its Action list is
# still the older spelling ("Renewal (Non-Kuwaiti)", "Extend 1 month"), so copying the
# table over would undo a rename already shipped here. The option comes with the doctype
# JSON; the row is seeded below.
ACTION = "Visa Costing"
WORK_PERMIT_AMOUNT = 20

# The costing table is read from HR Settings and nowhere else. A superseded "GRD Settings"
# Single still holds a dead copy of these rows that nothing reads.
PARENT = "HR Settings"


def execute():
	settings = frappe.get_single(PARENT)

	# An Action already configured is left exactly as it is. Somebody may have set the fee
	# to something other than 20 deliberately, and a patch that reran would otherwise walk
	# that correction back every migrate.
	for row in settings.get("renewal_extension_cost") or []:
		if row.renewal_or_extend == ACTION:
			return

	settings.append("renewal_extension_cost", {
		"renewal_or_extend": ACTION,
		"work_permit_amount": WORK_PERMIT_AMOUNT,
	})
	# A normal save so HR Settings' own validate hook totals the row, rather than a direct
	# insert that would leave Total Amount at zero against a 20 KWD component.
	settings.save(ignore_permissions=True)

	verify()


def verify():
	"""The row this patch adds is there, and carries the fee it was added for."""
	row = frappe.db.get_value(
		"GRD Renewal Extension Cost",
		{"parent": PARENT, "parenttype": PARENT, "renewal_or_extend": ACTION},
		["work_permit_amount", "total_amount"],
		as_dict=True,
	)
	if not row:
		frappe.throw(f"{ACTION} was not added to the {PARENT} costing table")
	if row.work_permit_amount != WORK_PERMIT_AMOUNT:
		frappe.throw(
			f"{ACTION} was added with a work permit amount of {row.work_permit_amount},"
			f" not {WORK_PERMIT_AMOUNT}"
		)
