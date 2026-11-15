import frappe

DOCTYPE = "Employee Record Update Request"

# The free-text `reason` field was replaced by `reason_for_changes` and `remarks`. Migrate keeps the
# orphaned `reason` column, so copy its text into empty `remarks`. `reason_for_changes` stays empty.


def execute():
	if not frappe.db.has_column(DOCTYPE, "reason"):
		return

	request = frappe.qb.DocType(DOCTYPE)
	(
		frappe.qb.update(request)
		.set(request.remarks, request.reason)
		.where(request.remarks.isnull() | (request.remarks == ""))
		.where(request.reason.isnotnull() & (request.reason != ""))
	).run()
