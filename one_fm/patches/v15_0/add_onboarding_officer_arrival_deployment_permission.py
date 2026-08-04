import frappe


def execute():
	"""Grant Onboarding Officer real access to Arrival and Deployment.

	The workflow already assigns Onboarding Officer as the owner of the
	Pending Support Departments / Joined / Did Not Arrive states, and as the
	allowed role on the "Submit to Support Departments" transition -- but the
	role was never actually granted read/write on the DocType itself (not in
	the DocType JSON's own permissions, not in Custom DocPerm). Every real
	Onboarding Officer in production currently also holds another role
	(HR Manager/HR User/Recruiter/etc.) that already grants access, which is
	why this has gone unnoticed -- but anyone assigned Onboarding Officer
	alone, exactly as the workflow is designed to support, would be blocked
	from the entire back half of this process.

	Custom DocPerm is currently completely empty for this doctype -- every
	other role (System Manager, HR Manager, HR User, Recruitment Manager,
	Recruiter, Senior Recruiter, Interviewer, Transportation Manager) is
	relying purely on the DocType JSON fallback. Adding a Custom DocPerm row
	for Onboarding Officer alone would immediately break all of them (same
	precedence rule as everywhere else this has come up today), so this
	mirrors every existing role in alongside the new grant.

	No submit/cancel granted anywhere: every state in this workflow stays at
	docstatus 0, it's driven entirely by workflow_state.
	"""
	existing_role_perms = {
		"System Manager": {"read": 1, "write": 1},
		"HR Manager": {"read": 1, "write": 1},
		"HR User": {"read": 1, "write": 1},
		"Recruitment Manager": {"read": 1, "write": 1},
		"Recruiter": {"read": 1, "write": 1},
		"Senior Recruiter": {"read": 1, "write": 1},
		"Interviewer": {"read": 1, "write": 1},
		"Transportation Manager": {"read": 1, "write": 1},
		"Onboarding Officer": {"read": 1, "write": 1},
	}

	for role, perms in existing_role_perms.items():
		if frappe.db.exists("Custom DocPerm", {"parent": "Arrival and Deployment", "role": role}):
			continue
		frappe.get_doc({
			"doctype": "Custom DocPerm",
			"parent": "Arrival and Deployment",
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": role,
			"permlevel": 0,
			**perms,
		}).insert()

	frappe.clear_cache(doctype="Arrival and Deployment")
