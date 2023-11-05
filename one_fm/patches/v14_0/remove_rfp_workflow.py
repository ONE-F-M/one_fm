import frappe

def execute():
	if frappe.db.exists('Workflow', {'name': 'RFP', 'document_type': 'Request for Purchase'}):
		frappe.delete_doc("Workflow", 'RFP')
