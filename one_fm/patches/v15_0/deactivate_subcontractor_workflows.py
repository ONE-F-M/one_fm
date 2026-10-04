import frappe

# Processa drives these states; its apply_workflow sets workflow_state directly when no Workflow is active.
WORKFLOWS = (
	"Subcontract Staff Request",
	"Subcontract Staff Shortlist",
	"Subcontractor Contracts",
	"Onboard Subcontract Employee",
	"Subcontract Staff Attendance",
	"Subcontractor Exit",
)


def execute():
	for name in WORKFLOWS:
		document_type = frappe.db.get_value("Workflow", name, "document_type")
		if not document_type:
			continue
		frappe.db.set_value("Workflow", name, "is_active", 0)
		frappe.cache.hdel("workflow", document_type)
		frappe.clear_cache(doctype=document_type)
