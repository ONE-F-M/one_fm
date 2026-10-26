import frappe

# The Processa Client Event map drives every state change and assigns every review task.
# An active Workflow adds Actions that move the record without the process instance,
# and the assignment rules would assign each stage a second time.
ASSIGNMENT_RULES = (
	"Client Event - Draft",
	"Client Event - Pending Project Manager",
	"Client Event - Pending Operations Manager",
)


def execute():
	if frappe.db.exists("Workflow", "Client Event"):
		frappe.db.set_value("Workflow", "Client Event", "is_active", 0)
		frappe.cache.hdel("workflow", "Client Event")

	for name in ASSIGNMENT_RULES:
		if frappe.db.exists("Assignment Rule", name):
			frappe.db.set_value("Assignment Rule", name, "disabled", 1)

	frappe.clear_cache(doctype="Client Event")
