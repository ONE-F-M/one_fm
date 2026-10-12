import frappe

ASSIGNMENT_RULES = (
	"Client Interview Shortlist - Draft",
	"Client Interview Shortlist - Pending Operations Manager",
	"Client Interview Shortlist - Pending Operations Supervisor",
	"Review & Approve Client Interview Shortlist - Operations Manager",
	"Submit Client Interview Shortlist - Operations Supervisor",
)


def execute():
	# The Processa Client Interview Shortlist map assigns every step itself; the rules
	# would assign each record a second time.
	for rule in ASSIGNMENT_RULES:
		frappe.delete_doc("Assignment Rule", rule, ignore_missing=True, ignore_permissions=True)

	# Deactivated rather than deleted: Process Tasks can be linked from ToDos and Tasks.
	frappe.db.set_value(
		"Process Task",
		{"erp_document": "Client Interview Shortlist", "task": "Review and Approve Client Interview Shortlist"},
		"is_active",
		0,
	)
