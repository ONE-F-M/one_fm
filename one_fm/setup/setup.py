import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import (
	make_property_setter, delete_property_setter
)
from one_fm.setup.custom_field import get_custom_fields
from one_fm.setup.property_setter import get_field_properties
from one_fm.setup.workflow import create_workflows, delete_workflows
from one_fm.setup.assignment_rule import create_assignment_rules, delete_assignment_rules


def after_install():
	_create_custom_fields_resiliently(get_custom_fields())
	add_property_setter(get_field_properties())
	create_workflows()
	create_assignment_rules()
	frappe.db.commit()

def _create_custom_fields_resiliently(custom_fields: dict):
	"""create_custom_fields() processes every doctype in the dict as one
	batch — it only tolerates frappe.exceptions.DuplicateEntryError per
	field, so a genuine fieldname conflict (which raises ValidationError,
	e.g. "A field with the name X already exists") is uncaught and aborts
	the entire call, silently skipping every doctype that was still queued
	after the one that conflicted. Confirmed live: Employee's "iban" field
	conflicting on a fresh install aborted before ever reaching Warehouse's
	fields (get_warehouse_custom_fields() is called much later in
	get_custom_fields()' chain), even though nothing about Warehouse's own
	fields was wrong.

	Isolate each doctype into its own call so one conflict can't take down
	unrelated doctypes' custom fields — it's logged instead, same as any
	other install-time issue that shouldn't block the rest of setup."""
	for doctype, fields in custom_fields.items():
		try:
			create_custom_fields({doctype: fields})
		except Exception:
			frappe.log_error(
				title=f"one_fm after_install: failed to create custom fields for {doctype}",
				message=frappe.get_traceback(),
			)

def before_uninstall():
	delete_custom_fields(get_custom_fields())
	remove_property_setter(get_field_properties())
	delete_workflows()
	delete_assignment_rules()
	frappe.db.commit()

def add_property_setter(property_setters):
	for property in property_setters:
		make_property_setter(
			doctype=property.get("doc_type"),
			fieldname=property.get("field_name"),
			property=property.get("property"),
			value=property.get("value"),
			property_type=property.get("property_type"),
			for_doctype=property.get("doctype_or_field") == "DocType",
			validate_fields_for_doctype=False
		)

def delete_custom_fields(custom_fields: dict):
	"""
	:param custom_fields: a dict like `{'Salary Slip': [{fieldname: 'loans', ...}]}`
	"""
	for doctype, fields in custom_fields.items():
		frappe.db.delete(
			"Custom Field",
			{
				"fieldname": ("in", [field["fieldname"] for field in fields]),
				"dt": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)

def remove_property_setter(property_setters):
	for property in property_setters:
		property_name = property.get("property")
		doc_type = property.get("doc_type")
		if property_name:
			delete_property_setter(
				doc_type=doc_type,
				property=property_name,
				field_name=property.get("field_name"),
				row_name=property.get("row_name")
			)

			frappe.clear_cache(doctype=doc_type)
