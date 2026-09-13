import frappe
from frappe.query_builder import DocType


def execute():
	"""
	Employee Checkin's Source field no longer defaults to "Check-in Form"
	(see update_employee_checkin_form_customizations). Existing records that
	picked up that old default should have it cleared too.

	Batched (instead of one large UPDATE) since this table is large
	(millions of rows) and `source` isn't indexed. Only `source` is set -
	`modified`/`modified_by` are intentionally left untouched.
	"""
	employee_checkin = DocType("Employee Checkin")
	batch_size = 5000

	while True:
		(
			frappe.qb.update(employee_checkin)
			.set(employee_checkin.source, "")
			.where(employee_checkin.source == "Check-in Form")
			.limit(batch_size)
		).run()

		# Read rowcount before commit() - commit() runs its own query on the
		# same cursor and would otherwise overwrite it.
		affected = frappe.db._cursor.rowcount
		frappe.db.commit()

		if not affected:
			break
