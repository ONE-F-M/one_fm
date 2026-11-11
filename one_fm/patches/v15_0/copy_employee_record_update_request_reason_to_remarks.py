import frappe

DOCTYPE = "Employee Record Update Request"

# WI-004577: the free-text `reason` field was replaced by `reason_for_changes` (dropdown) and
# `remarks`. Migrate does not drop the removed column, so existing records keep their text in
# the orphaned `reason` column, invisible on the form. Copy it into `remarks` so it stays readable.
#
# `reason_for_changes` is left empty on old records: there is no reliable mapping from free text.
# Idempotent: only rows whose remarks are still empty are touched, and the patch does nothing
# when the `reason` column is absent (fresh sites).


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
