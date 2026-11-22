import frappe


def execute():
	for doctype in ("Workflow", "Assignment Rule"):
		for name in frappe.get_all(doctype, filters={"document_type": "POC Check"}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)

	frappe.clear_cache(doctype="POC Check")
