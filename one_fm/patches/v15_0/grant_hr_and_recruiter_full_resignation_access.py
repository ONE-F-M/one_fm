import frappe
from frappe.permissions import add_permission, update_permission_property

# Give HR User, Recruiter, and HR Manager the same full access as System
# Manager across the whole resignation-to-replacement pipeline. Some of these
# were already there (HR Manager on Withdrawal and Date Adjustment, Recruiter
# on PMR) -- this only adds what's missing rather than re-granting everything
# everywhere.
GRANTS = [
	("Employee Resignation", "HR User"),
	("Employee Resignation", "Recruiter"),
	("Employee Resignation", "HR Manager"),
	("Employee Resignation Withdrawal", "HR User"),
	("Employee Resignation Withdrawal", "Recruiter"),
	("Employee Resignation Date Adjustment", "HR User"),
	("Employee Resignation Date Adjustment", "Recruiter"),
	("Project Manpower Request", "HR User"),
	("Project Manpower Request", "HR Manager"),
]

# read is set to 1 by add_permission() itself; these are the rest of what
# "same as System Manager" means.
FULL_ACCESS_PTYPES = ["write", "create", "submit", "cancel", "delete", "share", "report", "export", "print", "email"]


def execute():
	for doctype, role in GRANTS:
		grant_full_access(doctype, role)


def grant_full_access(doctype, role):
	if not frappe.db.exists("Role", role):
		frappe.log_error(
			title="Resignation Permissions: missing Role",
			message=f"Could not grant {role} access to {doctype} -- Role does not exist.",
		)
		return

	# add_permission() calls setup_custom_perms() internally, which copies the
	# doctype's existing DocPerm rows into Custom DocPerm the first time any
	# custom row is needed -- necessary here since Employee Resignation Date
	# Adjustment has no Custom DocPerm rows yet, and Custom DocPerm entirely
	# replaces (not merges with) DocPerm the moment any row exists for a
	# doctype. Without this, adding a role directly would silently strip every
	# other role's access on that doctype.
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
		add_permission(doctype, role, 0)

	for ptype in FULL_ACCESS_PTYPES:
		update_permission_property(doctype, role, 0, ptype, 1)
