# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	return get_columns(filters), get_data(filters)


def get_data(filters):
	doctype = frappe.get_meta(filters.doctype)
	links = []
	for x in doctype.get_link_fields():
		if not x.options in links:
			links.append(x.options)
	if not filters.show_permissions:
		return [{"doctype": x} for x in links]
	if not filters.doctype in links:
		links.append(filters.doctype)
	print(links)
	all_permissions = [frappe.get_meta(doclink).get_permissions() for doclink in links]
	permissions = []

	for y in all_permissions:
		for x in y:
			permissions.append(frappe._dict({
				'role': x.role,
				'select': x.select,
				'read': x.read,
				'write': x.write,
				'create': x.create,
				'delete': x.delete,
				'submit': x.submit,
				'cancel': x.cancel,
				'doctype': x.parent,
			})
			)
	return permissions


def get_columns(filters):
	if not filters.show_permissions:
		return [
			{
				"label": _("Doctype"),
				"fieldname": "doctype",
				"fieldtype": "Data",
				"width": 180
			}]
	columns = [
		{
			"label": _("Doctype"),
			"fieldname": "doctype",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("Role"),
			"fieldname": "role",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("Select"),
			"fieldname": "select",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Read"),
			"fieldname": "read",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Write"),
			"fieldname": "write",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Create"),
			"fieldname": "create",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Delete"),
			"fieldname": "delete",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Submit"),
			"fieldname": "submit",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Cancel"),
			"fieldname": "cancel",
			"fieldtype": "Data",
			"width": 80
		},
	]

	return columns

