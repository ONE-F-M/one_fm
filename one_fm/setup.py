import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.property_setter.property_setter import create_property_setter, delete_property_setter
from one_fm.custom.workflow.workflow import get_workflow, create_workflow, delete_workflow
from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule, create_assignment_rule, delete_assignment_rule

# Custom field imports
from one_fm.custom.custom_field.buying import get_supplier_group_custom_fields
from one_fm.custom.custom_field.payroll import get_additional_salary_custom_fields
from one_fm.custom.custom_field.automation import get_assignment_rule_custom_fields
from one_fm.custom.property_setter.automation import get_assignment_rule_properties

def after_install():
	create_custom_fields(get_custom_fields())
	create_property_setter(get_field_properties())
	create_workflows()
	create_assignment_rules()

def before_uninstall():
	delete_custom_fields(get_custom_fields())
	delete_property_setter(get_field_properties())
	delete_workflows()
	delete_assignment_rules()

def get_custom_fields():
	"""ONEFM specific custom fields that need to be added to the masters in ERPNext"""
	custom_fields = get_additional_salary_custom_fields()
	custom_fields.update(get_supplier_group_custom_fields())
	custom_fields.update(get_assignment_rule_custom_fields())
	return custom_fields

def get_field_properties():
	"""ONEFM specific field properties that need to be added to the masters in ERPNext"""
	field_properties = get_assignment_rule_properties()
	return field_properties

def create_workflows():
	pass

def create_assignment_rules():
	pass

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

def delete_workflows():
	pass

def delete_assignment_rules():
	pass
