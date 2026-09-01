import frappe


def execute():
	"""
	Employee Checkin's Source field no longer defaults to "Check-in Form"
	(see update_employee_checkin_form_customizations). Existing records that
	picked up that old default should have it cleared too.

	Batched (instead of one large UPDATE) since this table is large
	(millions of rows) and `source` isn't indexed.
	"""
	batch_size = 5000
	total_updated = 0

	while True:
		frappe.db.sql(
			"""
			UPDATE `tabEmployee Checkin`
			SET `source` = %s
			WHERE `source` = %s
			LIMIT %s
			""",
			("", "Check-in Form", batch_size),
		)
		# Read rowcount before commit() - commit() runs its own query on the
		# same cursor and would otherwise overwrite it.
		affected = frappe.db._cursor.rowcount
		frappe.db.commit()

		if not affected:
			break

		total_updated += affected
		frappe.logger().info(
			f"[Employee Checkin Source Backfill] Cleared {total_updated} records so far"
		)

	frappe.logger().info(
		f"[Employee Checkin Source Backfill] Done. Total records updated: {total_updated}"
	)
