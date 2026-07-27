import frappe

REFERENCE_TYPE = "Medical Appointment"
REFERENCE_NAMES = ["MAP-2026-00114", "MAP-2026-00108"]


def execute():
	"""Delete orphaned ToDo records referencing specific Medical Appointment documents."""
	todos = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": REFERENCE_TYPE,
			"reference_name": ["in", REFERENCE_NAMES],
		},
		pluck="name",
	)

	if not todos:
		print("Patch delete_medical_appointment_todos: No matching ToDo records found.")
		return

	for name in todos:
		frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)

	frappe.db.commit()
	print(f"Patch delete_medical_appointment_todos: Deleted {len(todos)} ToDo record(s).")
