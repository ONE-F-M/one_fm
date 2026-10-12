import frappe


def execute():
	# The Processa absence maps assign the review step themselves; the rule would
	# assign every case a second time.
	frappe.delete_doc("Assignment Rule", "Absence Case - HR Officer", ignore_missing=True, ignore_permissions=True)

	# Deactivated rather than deleted: Process Tasks can be linked from ToDos and Tasks.
	frappe.db.set_value(
		"Process Task",
		{"process_name": "Absence", "erp_document": "Absence Case", "task": "Assigning HR Officer"},
		"is_active",
		0,
	)
