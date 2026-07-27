import frappe


def execute():
	"""Delete Pending Approval Attendance Checks for Airport Terminal 4 on 2026-07-12."""

	attendance_checks = frappe.get_all(
		"Attendance Check",
		filters={
			"workflow_state": "Pending Approval",
			"operations_site": "Airport Terminal 4",
			"date": "2026-07-12",
		},
		pluck="name",
	)

	deleted_count = 0

	for name in attendance_checks:
		try:
			frappe.delete_doc(
				"Attendance Check", name, force=True, ignore_permissions=True
			)
			deleted_count += 1
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(
				message=f"Error deleting Attendance Check {name}: {str(e)}",
				title="Delete Airport T4 Attendance Checks Patch",
			)
			frappe.db.rollback()

	print(
		f"Successfully deleted {deleted_count} Pending Approval Attendance Check "
		f"records for Airport Terminal 4 on 2026-07-12."
	)
