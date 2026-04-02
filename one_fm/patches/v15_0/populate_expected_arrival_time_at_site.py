import frappe

def execute():
	# Populate 'expected_arrival_time_at_site' with the value of 'end_time' for existing records.

	# Reload the DocType to ensure the new field exists in the database.
	frappe.reload_doc("operations", "doctype", "operations_shift")

	if not frappe.db.has_column("Operations Shift", "expected_arrival_time_at_site"):
		return

	frappe.db.sql("""
		UPDATE `tabOperations Shift`
		SET expected_arrival_time_at_site = end_time
		WHERE expected_arrival_time_at_site IS NULL
	""")
