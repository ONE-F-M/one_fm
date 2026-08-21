import frappe


def execute():
	"""Grant Onboarding Officer real access to Arrival and Deployment -- at
	*both* permission levels this doctype actually uses.

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
	relying purely on the DocType JSON fallback, which grants each of them
	permlevel 0 (base read/write) *and* permlevel 1 (see
	set_arrival_deployment_workflow_state_permlevel.py -- workflow_state
	itself lives at permlevel 1, specifically so Transportation Manager could
	be granted write on just that one field). Adding a Custom DocPerm row at
	permlevel 0 only, as an earlier version of this patch did, replaces the
	*entire* permissions list Frappe resolves for this doctype -- silently
	discarding the permlevel 1 grant for all 8 existing roles along with it.
	Confirmed directly: with only the permlevel 0 rows in place,
	apply_workflow() for "Submit to Support Departments" returns without
	error but workflow_state is silently reverted back to its prior value on
	save (Document.reset_values_if_no_permlevel_access) for every role,
	Onboarding Officer included -- nobody but Administrator could actually
	drive this workflow forward. This version mirrors both permission levels
	for all 9 roles, so nothing regresses and Onboarding Officer gets the
	same real capability as everyone else.

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
		for permlevel in (0, 1):
			if frappe.db.exists("Custom DocPerm", {"parent": "Arrival and Deployment", "role": role, "permlevel": permlevel}):
				continue
			frappe.get_doc({
				"doctype": "Custom DocPerm",
				"parent": "Arrival and Deployment",
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": role,
				"permlevel": permlevel,
				**perms,
			}).insert()

	frappe.clear_cache(doctype="Arrival and Deployment")
