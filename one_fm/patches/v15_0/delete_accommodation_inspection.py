import frappe

DOCTYPES = ("Accommodation Inspection", "Accommodation Inspection Reading")

# Rows elsewhere that only exist because the doctype did. Frappe clears these
# when a document is deleted one at a time; dropping the table skips all of it.
TRAILS = (
	("Workflow Action", "reference_doctype"),
	("Custom Field", "dt"),
	("Property Setter", "doc_type"),
	("Custom DocPerm", "parent"),
	("DocShare", "share_doctype"),
	("ToDo", "reference_type"),
	("Comment", "reference_doctype"),
	("Version", "ref_doctype"),
	("Communication", "reference_doctype"),
	("File", "attached_to_doctype"),
	("Activity Log", "reference_doctype"),
	("Tag Link", "document_type"),
	("Workspace Link", "link_to"),
)


def execute():
	"""Drop Accommodation Inspection and the child table only it used.

	Deleting the DocType leaves its table behind under `bench migrate`, so the
	drop is explicit. Accommodation Inspection Template and Parameter are kept.
	Safe to run more than once.
	"""
	for doctype, field in TRAILS:
		if frappe.db.exists("DocType", doctype):
			frappe.db.delete(doctype, {field: ["in", DOCTYPES]})

	frappe.db.delete("Report", {"ref_doctype": ["in", DOCTYPES]})

	for doctype in DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
		frappe.db.sql_ddl("drop table if exists `tab{0}`".format(doctype))

	frappe.clear_cache()
