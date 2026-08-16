import frappe
from frappe.permissions import add_permission, update_permission_property

# (doctype, role, needs_submit)
GRANTS = [
	("Employee Resignation", "Cleaning Head Supervisor", False),
	("Employee Resignation", "Security Manager", False),
	("Employee Resignation", "Project Manager", True),
	("Employee Resignation Withdrawal", "T4 Admin", False),
	("Employee Resignation Withdrawal", "Cleaning Head Supervisor", False),
	("Employee Resignation Withdrawal", "Security Manager", False),
	("Employee Resignation Withdrawal", "Project Manager", True),
]

STALE_ROLE = "Operations Manager"
STALE_ROLE_DOCTYPES = ["Employee Resignation", "Employee Resignation Withdrawal"]


def execute():
	"""The v2 branch-routing workflow (add_resignation_v2_branch_routing) introduced
	T4 Admin / Cleaning Head Supervisor / Security Manager / Project Manager as new
	workflow actors on Employee Resignation and Employee Resignation Withdrawal, but
	never granted them Custom DocPerm rows. Both doctypes already have Custom DocPerm
	rows for other roles, which means the DocType-JSON-declared permissions no longer
	apply at all -- without an explicit row, these roles have zero access and can't
	open the very documents the workflow routes to them. Also drops the now-stale
	"Operations Manager" grant on both doctypes, since that role is no longer a
	workflow actor anywhere in the redesigned process.
	"""
	for doctype, role, needs_submit in GRANTS:
		grant_access(doctype, role, submit=needs_submit)

	for doctype in STALE_ROLE_DOCTYPES:
		remove_stale_role(doctype, STALE_ROLE)


def grant_access(doctype, role, submit=False):
	if not frappe.db.exists("Role", role):
		frappe.log_error(
			title="Employee Resignation v2: missing Role",
			message=f"Could not grant {role} access to {doctype} -- Role does not exist yet.",
		)
		return

	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
		add_permission(doctype, role, 0)

	update_permission_property(doctype, role, 0, "write", 1)
	if submit:
		update_permission_property(doctype, role, 0, "submit", 1)


def remove_stale_role(doctype, role):
	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role})
