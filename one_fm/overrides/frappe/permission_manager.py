# Copyright (c) 2024, One FM and contributors
# License: See LICENSE

"""
Overrides for frappe.core.page.permission_manager.permission_manager

Routes all Role Permissions Manager changes (add, update, remove, reset)
to the frappe Version doctype for audit trail purposes.
"""

import frappe
from frappe import _
from frappe.core.doctype.doctype.doctype import (
	clear_permissions_cache,
	validate_permissions_for_doctype,
)
from frappe.permissions import (
	add_permission,
	reset_perms,
	setup_custom_perms,
	update_permission_property,
)
@frappe.whitelist()
def add(parent, role, permlevel):
	frappe.only_for("System Manager")

	name = add_permission(parent, role, permlevel)

	if name:
		doc = frappe.get_doc("Custom DocPerm", name)
		_create_version(
			docname=name,
			perm_doctype=doc.parent,
			perm_role=doc.role,
			perm_level=doc.permlevel,
			perm_if_owner=doc.if_owner,
			data={
				"changed": [],
				"added": [[name, doc.as_dict()]],
				"removed": [],
				"row_changed": [],
				"updater_reference": {
					"doctype": "Permission Manager",
					"label": "Added via Role Permissions Manager",
				},
			},
		)


@frappe.whitelist()
def update(doctype, role, permlevel, ptype, value=None, if_owner=0):
	"""Update role permission params and log the change to Version."""

	def clear_cache():
		frappe.clear_cache(doctype=doctype)

	frappe.only_for("System Manager")

	if ptype == "report" and value == "1" and if_owner == "1":
		frappe.throw(_("Cannot set 'Report' permission if 'Only If Creator' permission is set"))

	# Capture old value before the update
	name = frappe.db.get_value(
		"Custom DocPerm",
		dict(parent=doctype, role=role, permlevel=permlevel, if_owner=if_owner),
	)
	old_value = None
	if name:
		old_value = frappe.db.get_value("Custom DocPerm", name, ptype)

	out = update_permission_property(doctype, role, permlevel, ptype, value, if_owner=if_owner)

	# Re-fetch name in case update_permission_property() promoted a standard DocPerm
	# to a Custom DocPerm (name would have been None before the update)
	if not name:
		name = frappe.db.get_value(
			"Custom DocPerm",
			dict(parent=doctype, role=role, permlevel=permlevel, if_owner=if_owner),
		)

	if ptype == "if_owner" and value == "1":
		update_permission_property(doctype, role, permlevel, "report", "0", if_owner=value)

	frappe.db.after_commit.add(clear_cache)

	# Log to Version — use the resolved if_owner value when ptype is "if_owner"
	effective_if_owner = value if ptype == "if_owner" else if_owner
	if name and old_value != value:
		_create_version(
			docname=name,
			perm_doctype=doctype,
			perm_role=role,
			perm_level=permlevel,
			perm_if_owner=effective_if_owner,
			data={
				"changed": [[ptype, old_value, value]],
				"added": [],
				"removed": [],
				"row_changed": [],
				"updater_reference": {
					"doctype": "Permission Manager",
					"label": "Updated via Role Permissions Manager",
				},
			},
		)

	return "refresh" if out else None


@frappe.whitelist()
def remove(doctype, role, permlevel, if_owner=0):
	frappe.only_for("System Manager")
	setup_custom_perms(doctype)

	name = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": permlevel, "if_owner": if_owner},
	)

	if not name:
		# No matching Custom DocPerm found — nothing to version or delete
		return

	doc = frappe.get_doc("Custom DocPerm", name)
	# Version must be created before the row is deleted
	_create_version(
		docname=name,
		perm_doctype=doc.parent,
		perm_role=doc.role,
		perm_level=doc.permlevel,
		perm_if_owner=doc.if_owner,
		data={
			"changed": [],
			"added": [],
			"removed": [[name, doc.as_dict()]],
			"row_changed": [],
			"updater_reference": {
				"doctype": "Permission Manager",
				"label": "Removed via Role Permissions Manager",
			},
		},
	)
	# Delete by the resolved name to keep deletion and Version entry consistent
	frappe.db.delete("Custom DocPerm", {"name": name})

	if not frappe.get_all("Custom DocPerm", {"parent": doctype}):
		frappe.throw(_("There must be atleast one permission rule."), title=_("Cannot Remove"))

	validate_permissions_for_doctype(doctype, for_remove=True, alert=True)


@frappe.whitelist()
def reset(doctype):
	frappe.only_for("System Manager")

	# Version every existing Custom DocPerm row before the bulk wipe
	for perm in frappe.get_all("Custom DocPerm", filters={"parent": doctype}, fields=["name"]):
		doc = frappe.get_doc("Custom DocPerm", perm.name)
		_create_version(
			docname=perm.name,
			perm_doctype=doc.parent,
			perm_role=doc.role,
			perm_level=doc.permlevel,
			perm_if_owner=doc.if_owner,
			data={
				"changed": [],
				"added": [],
				"removed": [[perm.name, doc.as_dict()]],
				"row_changed": [],
				"updater_reference": {
					"doctype": "Permission Manager",
					"label": "Removed via Role Permissions Manager Reset",
				},
			},
		)

	reset_perms(doctype)
	clear_permissions_cache(doctype)


def _create_version(docname, data, perm_doctype=None, perm_role=None, perm_level=None, perm_if_owner=None):
	"""Insert a Version record for a Custom DocPerm change."""
	version = frappe.new_doc("Version")
	version.ref_doctype = "Custom DocPerm"
	version.docname = docname
	version.data = frappe.as_json(data, indent=None, separators=(",", ":"))

	meta = version.meta
	if perm_doctype is not None and meta.has_field("perm_doctype"):
		version.perm_doctype = perm_doctype
	if perm_role is not None and meta.has_field("perm_role"):
		version.perm_role = perm_role
	if perm_level is not None and meta.has_field("perm_level"):
		version.perm_level = perm_level
	if perm_if_owner is not None and meta.has_field("perm_if_owner"):
		version.perm_if_owner = perm_if_owner
	version.insert(ignore_permissions=True)
