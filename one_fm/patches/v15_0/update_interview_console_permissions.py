import frappe

def setup_permissions(doctype, role, perms):
	# 1. If no Custom DocPerm exists for this doctype, copy all standard DocPerms to Custom DocPerm first
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
		standard_perms = frappe.get_all("DocPerm", filters={"parent": doctype}, fields="*")
		for sp in standard_perms:
			custom_perm = frappe.new_doc("Custom DocPerm")
			# Copy values
			for key, val in sp.items():
				if key not in ["name", "owner", "creation", "modified", "modified_by"]:
					custom_perm.set(key, val)
			custom_perm.parent = doctype
			custom_perm.parenttype = "DocType"
			custom_perm.parentfield = "permissions"
			custom_perm.insert(ignore_permissions=True)

	# 2. Check if a Custom DocPerm already exists for this doctype and role
	custom_perm_name = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role})

	if custom_perm_name:
		custom_perm = frappe.get_doc("Custom DocPerm", custom_perm_name)
	else:
		custom_perm = frappe.new_doc("Custom DocPerm")
		custom_perm.parent = doctype
		custom_perm.parenttype = "DocType"
		custom_perm.parentfield = "permissions"
		custom_perm.role = role
		custom_perm.permlevel = 0

	# 3. Update permissions dictionary
	for k, v in perms.items():
		custom_perm.set(k, v)

	custom_perm.save(ignore_permissions=True)

def execute():
	print("Starting Permission Update for Interview-related DocTypes...")

	target_roles = [
		"Interviewer",
		"HR User",
		"Recruiter",
		"HR Manager",
		"Senior Recruiter",
		"System Manager"
	]

	full_perms = {
		"read": 1,
		"write": 1,
		"create": 1,
		"submit": 1,
		"cancel": 1,
		"amend": 1,
		"select": 1,
		"export": 1,
		"share": 1,
		"email": 1,
		"print": 1,
		"report": 1
	}

	round_perms = {
		"read": 1,
		"write": 1,
		"create": 1,
		"select": 1,
		"export": 1,
		"share": 1,
		"email": 1,
		"print": 1,
		"report": 1
	}

	for role in target_roles:
		setup_permissions("Interview Feedback", role, full_perms)
		setup_permissions("Interview", role, full_perms)
		setup_permissions("Interview Round", role, round_perms)

	frappe.db.commit()
	
	frappe.clear_cache(doctype="Interview Feedback")
	frappe.clear_cache(doctype="Interview")
	frappe.clear_cache(doctype="Interview Round")
	
	print("Permissions updated and cache cleared successfully!")
