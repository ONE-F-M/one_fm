import frappe


def execute():
	"""Add Onboarding Officer's Custom DocPerm on Candidate Country Process, and
	backfill Custom DocPerm entries for roles that were only ever defined in the
	DocType's own JSON permissions.

	Candidate Country Process already has Custom DocPerm records for System Manager
	and Recruiter (added directly via the Desk UI back in May, well before this
	patch). Once any Custom DocPerm exists for a doctype, Frappe's permission
	resolution (frappe.permissions.get_valid_perms) stops honouring that doctype's
	plain DocPerm/JSON-defined permissions entirely for every OTHER role, falling
	back to Custom DocPerm exclusively. That silently left HR Manager, HR User,
	Recruitment Manager, Interviewer, and Agency with no real access to this
	doctype in the database, despite all of them being listed in the DocType JSON
	with real permissions.

	Onboarding Officer only gets read/print/report/share here at the permission
	level — write is additionally granted, then conditionally denied back by
	candidate_country_process.has_permission() until the linked Arrival and
	Deployment record reaches "Pending Onboarding" or later.
	"""
	role_perms = {
		"Onboarding Officer": {"read": 1, "write": 1, "print": 1, "report": 1, "share": 1},
		"HR Manager": {
			"read": 1, "write": 1, "create": 1, "delete": 1, "cancel": 1, "submit": 1,
			"email": 1, "export": 1, "import": 1, "print": 1, "report": 1, "share": 1,
		},
		"HR User": {
			"read": 1, "write": 1, "create": 1, "delete": 1, "cancel": 1, "submit": 1,
			"email": 1, "export": 1, "import": 1, "print": 1, "report": 1, "share": 1,
		},
		"Recruitment Manager": {
			"read": 1, "write": 1, "create": 1, "delete": 1,
			"email": 1, "export": 1, "print": 1, "report": 1, "share": 1,
		},
		"Interviewer": {"read": 1, "print": 1, "report": 1, "share": 1},
		"Agency": {"read": 1, "email": 1, "print": 1, "report": 1},
	}

	for role, perms in role_perms.items():
		if frappe.db.exists("Custom DocPerm", {"parent": "Candidate Country Process", "role": role}):
			continue
		frappe.get_doc({
			"doctype": "Custom DocPerm",
			"parent": "Candidate Country Process",
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": role,
			"permlevel": 0,
			**perms,
		}).insert()

	frappe.clear_cache(doctype="Candidate Country Process")
