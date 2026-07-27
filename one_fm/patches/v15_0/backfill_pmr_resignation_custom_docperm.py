import frappe


def execute():
	"""Backfill Custom DocPerm for T4 Admin (Project Manpower Request) and Operation
	Admin / T4 Admin (Employee Resignation), and grant Transportation Manager the same
	access as Operation Admin on both doctypes.

	Both doctypes already have Custom DocPerm records for other roles, and once any
	Custom DocPerm exists for a doctype, Frappe stops honouring that doctype's plain
	DocType-JSON permissions for every other role (same precedence rule discovered on
	Candidate Country Process earlier). Despite being listed in each doctype's own JSON
	with real permissions, T4 Admin (PMR) and Operation Admin / T4 Admin (Employee
	Resignation) currently have zero real access.

	Transportation Manager gets nothing on Employee Resignation Date Adjustment,
	matching Operation Admin's own zero access there -- a true mirror, not a
	broader grant.
	"""
	pmr_perms = {
		"select": 1, "read": 1, "write": 1, "create": 1, "delete": 1,
		"submit": 1, "cancel": 1, "amend": 1, "report": 1, "export": 1,
		"share": 1, "print": 1, "email": 1,
	}
	resignation_perms = {
		"read": 1, "write": 1, "report": 1, "export": 1, "share": 1, "print": 1, "email": 1,
	}

	grants = [
		("Project Manpower Request", "T4 Admin", pmr_perms),
		("Project Manpower Request", "Transportation Manager", pmr_perms),
		("Employee Resignation", "Operation Admin", resignation_perms),
		("Employee Resignation", "T4 Admin", resignation_perms),
		("Employee Resignation", "Transportation Manager", resignation_perms),
	]

	for doctype, role, perms in grants:
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
			continue
		frappe.get_doc({
			"doctype": "Custom DocPerm",
			"parent": doctype,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": role,
			"permlevel": 0,
			**perms,
		}).insert()

	frappe.clear_cache(doctype="Project Manpower Request")
	frappe.clear_cache(doctype="Employee Resignation")
