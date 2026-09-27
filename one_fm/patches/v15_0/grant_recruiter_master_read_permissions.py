import frappe
from frappe.permissions import add_permission, update_permission_property

# Masters linked from Job Applicant that no recruiter role could read. Each one
# 403s the form script's lookup and raises a bare "Not permitted" dialog, since
# the failing endpoint returns no message of its own.
GRANTS = {
	"Currency": ["Employee"],
	"PAM License Details": ["HR User", "Recruiter"],
	"Magic Link": ["HR User"],
}


def execute():
	"""Let recruiters read the masters their own Job Applicant form links to.

	Read only - these are lookup masters, nothing on them is edited from this form.
	Adding any Custom DocPerm row makes Frappe stop honouring the DocType JSON for
	every other role, which add_permission handles by copying the standard rows over
	first, so the existing holders keep exactly what they have.
	"""
	for doctype, roles in GRANTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		for role in roles:
			if not frappe.db.exists("Role", role):
				continue
			_grant_read(doctype, role)

	frappe.clear_cache()


def _grant_read(doctype: str, role: str):
	"""Add the role's read rule, or switch read on if the rule is already there."""
	existing = frappe.db.exists(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0},
	)

	if not existing:
		add_permission(doctype, role, 0)
		print(f"{doctype}: granted read to {role}")
		return

	if not frappe.db.get_value("Custom DocPerm", existing, "read"):
		update_permission_property(doctype, role, 0, "read", 1)
		print(f"{doctype}: enabled read for existing {role} rule")
