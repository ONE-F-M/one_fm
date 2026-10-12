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
	create_default_warehouse_types()
	_create_custom_fields_resiliently(get_custom_fields())
	add_property_setter(get_field_properties())
	set_todo_allocated_to_default()
	create_workflows()
	create_assignment_rules()
	frappe.db.commit()

def create_default_warehouse_types():
	"""ERPNext's Company.create_default_warehouses() hardcodes
	warehouse_type="Transit" when creating the default warehouses for a new
	Company. That "Warehouse Type" record is normally seeded only by
	ERPNext's interactive Setup Wizard (install_fixtures.install()), which
	one_fm's install/migrate flow never runs. Without it, creating a Company
	on a fresh site fails with:
		LinkValidationError: Could not find Warehouse Type: Transit
	Seed it here so it exists before any Company is ever created."""
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(
			ignore_permissions=True
		)

def set_todo_allocated_to_default():
	"""Frappe's test_runner.make_test_objects() attempts to create test ToDo records
	during test setup. The one_fm property setter makes 'allocated_to' mandatory on
	the ToDo DocType. However, frappe.get_doc() does not auto-populate mandatory fields
	without a default value set at the database level. Without this default, creating
	a test ToDo fails with:
		MandatoryError: [ToDo, ...]: allocated_to
	Set the default value at the database level so test records can be created."""
	try:
		frappe.db.set_value(
			"DocField",
			{"parent": "ToDo", "fieldname": "allocated_to"},
			"default",
			"Administrator",
			update_modified=False
		)
		frappe.clear_cache(doctype="ToDo")
	except Exception:
		# If setting the default fails (e.g., field doesn't exist yet), log it
		# but don't fail the install - the field will be there eventually
		frappe.log_error(
			title="one_fm after_install: failed to set default for ToDo.allocated_to",
			message=frappe.get_traceback(),
		)

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
