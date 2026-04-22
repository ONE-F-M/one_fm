import frappe


def after_insert(doc, event):
	"""
	:param doc:
	:param event:
	:return:
	"""
	contact_name = frappe.db.get_value("Contact", {"email_id": doc.email})
	is_subcontractor = False
	supplier = None

	if contact_name:
		links = frappe.get_all(
			"Dynamic Link",
			filters={"parent": contact_name, "parenttype": "Contact", "link_doctype": "Supplier"},
			fields=["link_name"]
		)
		if links:
			is_subcontractor = True
			supplier = links[0].link_name

	if not is_subcontractor and not doc.role_profile_name == "Only Employee":
		if frappe.db.exists({"doctype": "Employee", "user_id": doc.name}):
			doc.db_set("user_type", "System User")
			doc.db_set("role_profile_name", "Only Employee")

	if is_subcontractor and supplier:
		# Ensure Website User (portal-only)
		doc.db_set("user_type", "Website User")

		# Ensure Subcontractor role exists with desk_access = 0
		if not frappe.db.exists("Role", "Subcontractor"):
			frappe.get_doc({"doctype": "Role", "role_name": "Subcontractor", "desk_access": 0}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Role", "Subcontractor", "desk_access", 0)

		doc.add_roles("Subcontractor")

		# Create User Permission for Supplier (used to auto-populate the web form)
		if not frappe.db.exists("User Permission", {"user": doc.name, "allow": "Supplier", "for_value": supplier}):
			user_perm = frappe.new_doc("User Permission")
			user_perm.user = doc.name
			user_perm.allow = "Supplier"
			user_perm.for_value = supplier
			user_perm.insert(ignore_permissions=True)
