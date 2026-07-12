import frappe

def execute():
	if not frappe.db.exists("Custom DocPerm", {"parent": "Nationality", "role": "All"}):
		from frappe.permissions import add_permission
		add_permission("Nationality", "All", 0)
		custom_perm = frappe.get_doc("Custom DocPerm", {"parent": "Nationality", "role": "All"})
		custom_perm.read = 1
		custom_perm.write = 0
		custom_perm.create = 0
		custom_perm.save(ignore_permissions=True)
		frappe.db.commit()
