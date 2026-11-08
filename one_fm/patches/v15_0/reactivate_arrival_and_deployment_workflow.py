import frappe

# The Arrival and Deployment move to Processa was reverted; the Workflow drives the record again.


def execute():
	if frappe.db.exists("Workflow", "Arrival and Deployment"):
		frappe.db.set_value("Workflow", "Arrival and Deployment", "is_active", 1)
		frappe.cache.hdel("workflow", "Arrival and Deployment")

	frappe.clear_cache(doctype="Arrival and Deployment")
