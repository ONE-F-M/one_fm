import frappe


def execute():
	"""Drop Pathfinder Log and the child table only it used.

	Deleting the DocType leaves its table behind under `bench migrate`, so the
	drop is explicit — otherwise the records outlive the doctype.
	"""
	frappe.db.delete("Workflow Action", {"reference_doctype": "Pathfinder Log"})
	frappe.db.delete("Custom Field", {"dt": "Pathfinder Log"})
	frappe.db.delete("Property Setter", {"doc_type": "Pathfinder Log"})

	for doctype in ("Pathfinder Log", "Pathfinder Log Time"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
		frappe.db.sql_ddl("drop table if exists `tab{0}`".format(doctype))
