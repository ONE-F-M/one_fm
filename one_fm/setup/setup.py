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
	resolve_conflicting_custom_fields()
	create_custom_fields(get_custom_fields())
	add_property_setter(get_field_properties())
	create_workflows()
	create_assignment_rules()
	frappe.db.commit()


def resolve_conflicting_custom_fields():
	"""Delete HRMS-created custom fields whose fieldtype one_fm needs to change.

	HRMS creates `health_insurance_provider` on Employee as a Link field
	(→ Employee Health Insurance). one_fm redefines it as a Table field
	(→ Health Insurance Provider Detail) to support multiple providers.
	Frappe blocks fieldtype changes (Link→Table), so we must remove the
	HRMS version first.

	Called from both after_install and before_migrate (via hooks.py).
	"""
	conflicting = [
		{"dt": "Employee", "fieldname": "health_insurance_provider"},
	]
	for cf in conflicting:
		if frappe.db.exists("Custom Field", {"dt": cf["dt"], "fieldname": cf["fieldname"]}):
			existing_fieldtype = frappe.db.get_value(
				"Custom Field",
				{"dt": cf["dt"], "fieldname": cf["fieldname"]},
				"fieldtype",
			)
			# Only delete if it's the wrong type (HRMS's Link, not our Table)
			if existing_fieldtype == "Link":
				frappe.db.delete("Custom Field", {"dt": cf["dt"], "fieldname": cf["fieldname"]})
				frappe.clear_cache(doctype=cf["dt"])

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
