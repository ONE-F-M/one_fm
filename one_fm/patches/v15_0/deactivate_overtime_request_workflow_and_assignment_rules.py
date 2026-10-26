import frappe

# The Processa Overtime Request map drives every state change and assigns every review task.
# An active Workflow adds Actions that move the record without the process instance,
# and the assignment rules would assign each stage a second time.
ASSIGNMENT_RULES = (
	"Assign to Employee for Overtime Acceptance",
	"Pending Line Manager Approval",
	"Pending Payroll Officer Acknowledgment",
	"Pending Finance Manager Completion",
)


def execute():
	if frappe.db.exists("Workflow", "Overtime Request"):
		frappe.db.set_value("Workflow", "Overtime Request", "is_active", 0)
		frappe.cache.hdel("workflow", "Overtime Request")

	for name in ASSIGNMENT_RULES:
		if frappe.db.exists("Assignment Rule", name):
			frappe.db.set_value("Assignment Rule", name, "disabled", 1)

	frappe.clear_cache(doctype="Overtime Request")
