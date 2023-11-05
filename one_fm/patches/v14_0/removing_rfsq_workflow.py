import frappe

def execute():
	rfsq_workflow = frappe.db.exists('Workflow', {'document_type': 'Request for Supplier Quotation'})
	if rfsq_workflow:
		frappe.delete_doc("Workflow", rfsq_workflow)
		frappe.db.commit()
