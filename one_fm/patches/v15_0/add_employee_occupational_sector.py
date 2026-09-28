import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.employee import get_employee_custom_fields

FIELD = "Employee-custom_occupational_sector"
FIELDTYPE = "Link"


def execute():
	"""Add custom_occupational_sector to Employee.

	The definition in custom_field/employee.py is only applied by after_install, so on a
	site that is already installed a new entry in it never reaches the form.
	"""
	# The field shipped as Data and is a Link now. Frappe refuses that change outright -
	# ALLOWED_FIELDTYPE_CHANGE has no group holding both - so the Custom Field is deleted
	# and written again. Deleting it leaves the column and everything in it alone: the
	# Custom Field's on_trash clears caches and property setters and never touches the
	# table, so the field is recreated over the values that are already there.
	current = frappe.db.get_value("Custom Field", FIELD, "fieldtype")
	if current and current != FIELDTYPE:
		frappe.delete_doc("Custom Field", FIELD, ignore_missing=True)

	create_custom_fields(get_employee_custom_fields(), update=True)

	# Not redundant. create_custom_fields only syncs the table when it inserted or changed
	# a Custom Field; a row that is already there and already correct leaves the schema
	# alone. If that row's own ALTER failed earlier - tabEmployee runs close to InnoDB's
	# row limit, and DDL commits implicitly in MariaDB, so a failed ALTER leaves the
	# Custom Field behind without its column - nothing would ever add the column and every
	# save of an Employee dies on "Unknown column ... in 'SET'".
	frappe.db.updatedb("Employee")
