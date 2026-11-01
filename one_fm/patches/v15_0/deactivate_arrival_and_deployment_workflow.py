import frappe

# The Processa Arrival and Deployment map drives every state change and assigns every task.
# An active Workflow adds Actions that move the record without the process instance.


def execute():
	if frappe.db.exists("Workflow", "Arrival and Deployment"):
		frappe.db.set_value("Workflow", "Arrival and Deployment", "is_active", 0)
		frappe.cache.hdel("workflow", "Arrival and Deployment")

	frappe.clear_cache(doctype="Arrival and Deployment")
