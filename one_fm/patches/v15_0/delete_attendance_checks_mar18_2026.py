import frappe

def execute():
	"""
	Delete all Attendance Check records for projects 'T4 Airport' and 'Jazeera Airways' for 18th of March 2026
	"""
	sites = frappe.get_all(
		"Operations Site",
		filters={"project": ["in", ["T4 Airport", "Jazeera Airways"]]},
		pluck="name"
	)

	if not sites:
		return

	attendance_checks = frappe.get_all(
		"Attendance Check",
		filters={
			"operations_site": ["in", sites],
			"date": "2026-03-18",
			"workflow_state": "Pending Approval"
		},
		pluck="name"
	)

	for ac in attendance_checks:
		frappe.delete_doc("Attendance Check", ac, ignore_permissions=True, force=True)

	frappe.db.commit()
