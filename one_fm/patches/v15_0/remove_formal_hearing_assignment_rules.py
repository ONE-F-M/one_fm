import frappe

ASSIGNMENT_RULES = (
	"Formal Hearing - Operations Manager",
	"Formal Hearing - HR Manager",
	"Formal Hearing - General Manager",
)

PROCESS_TASKS = (
	"Assigning Operations Manager",
	"Assigning HR Manager",
	"Assigning General Manager",
)


def execute():
	# The Processa Conduct Formal Hearing map assigns every review step itself; the rules
	# would assign each hearing a second time.
	for rule in ASSIGNMENT_RULES:
		frappe.delete_doc("Assignment Rule", rule, ignore_missing=True, ignore_permissions=True)

	# Deactivated rather than deleted: Process Tasks can be linked from ToDos and Tasks.
	for task in PROCESS_TASKS:
		frappe.db.set_value(
			"Process Task",
			{"process_name": "Absence", "erp_document": "Formal Hearing", "task": task},
			"is_active",
			0,
		)
