# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# Permission actions exposed by a DocPerm / Custom DocPerm row.
PERMISSION_ACTIONS = [
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"print",
	"email",
	"share",
]


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.user:
		frappe.throw(_("Please select a User"))
	if not filters.target_doctype:
		frappe.throw(_("Please select a DocType"))

	# Only privileged users should inspect another user's roles/permissions.
	frappe.only_for(["System Manager", "Administrator"])

	columns = get_columns()
	data, summary = get_data(filters)
	return columns, data, None, None, summary


def get_columns():
	columns = [
		{
			"fieldname": "role",
			"label": _("Role"),
			"fieldtype": "Link",
			"options": "Role",
			"width": 220,
		},
		{
			"fieldname": "user_has_role",
			"label": _("User Has Role"),
			"fieldtype": "Check",
			"width": 110,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"fieldname": "permlevel",
			"label": _("Perm Level"),
			"fieldtype": "Int",
			"width": 90,
		},
	]
	for action in PERMISSION_ACTIONS:
		columns.append({
			"fieldname": action,
			"label": _(action.title()),
			"fieldtype": "Check",
			"width": 75,
		})
	return columns


def get_data(filters):
	# Roles the user currently holds (includes "All" / standard roles).
	user_roles = set(frappe.get_roles(filters.user))

	# Effective permissions for the doctype: returns Custom DocPerm rows when
	# the doctype has been customized, otherwise the standard DocPerm rows.
	meta = frappe.get_meta(filters.target_doctype)
	permissions = meta.get_permissions()

	data = []
	roles_with_perm = set()
	assignable_roles = set()

	for perm in permissions:
		user_has_role = 1 if perm.role in user_roles else 0
		roles_with_perm.add(perm.role)

		if user_has_role:
			status = _("Already assigned")
		else:
			status = _("Can be assigned")
			assignable_roles.add(perm.role)

		row = {
			"role": perm.role,
			"user_has_role": user_has_role,
			"status": status,
			"permlevel": perm.permlevel or 0,
		}
		for action in PERMISSION_ACTIONS:
			row[action] = perm.get(action) or 0

		data.append(row)

	# Sort: roles the user already has first, then by role name.
	data.sort(key=lambda r: (not r["user_has_role"], r["role"], r["permlevel"]))

	summary = get_report_summary(
		user_roles=user_roles,
		roles_with_perm=roles_with_perm,
		assignable_roles=assignable_roles,
	)
	return data, summary


def get_report_summary(user_roles, roles_with_perm, assignable_roles):
	already_assigned = roles_with_perm & user_roles
	return [
		{
			"value": len(user_roles),
			"label": _("Total Roles User Has"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": len(roles_with_perm),
			"label": _("Roles With Permission on DocType"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": len(already_assigned),
			"label": _("Permission Roles User Already Has"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": len(assignable_roles),
			"label": _("Permission Roles Available to Assign"),
			"datatype": "Int",
			"indicator": "orange" if assignable_roles else "green",
		},
	]
