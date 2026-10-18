import frappe

# The Processa Bonus map drives every state change and assigns every review task.
# An active Workflow adds Actions that move the record without the process instance,
# and the assignment rules would assign each stage a second time.
ASSIGNMENT_RULES = (
	"Bonus Request - Line Manager",
	"Bonus Request - HR Manager",
	"Bonus Request - General Manager",
	"Bonus Request - Finance Manager",
	"Bonus Request - Payroll Operator",
)


def execute():
	if frappe.db.exists("Workflow", "Bonus Request"):
		frappe.db.set_value("Workflow", "Bonus Request", "is_active", 0)
		frappe.cache.hdel("workflow", "Bonus Request")

	for name in ASSIGNMENT_RULES:
		if frappe.db.exists("Assignment Rule", name):
			frappe.db.set_value("Assignment Rule", name, "disabled", 1)

	frappe.clear_cache(doctype="Bonus Request")
