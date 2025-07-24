import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import (
	make_property_setter, delete_property_setter
)
from one_fm.custom.workflow.workflow import (
	get_workflow_json_file, create_workflow, delete_workflow
)
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule
)
# Custom field imports
from one_fm.custom.custom_field.supplier_group import get_supplier_group_custom_fields
from one_fm.one_fm.custom.custom_field.leave_type import get_leave_type_custom_fields
from one_fm.custom.custom_field.additional_salary import get_additional_salary_custom_fields
from one_fm.custom.custom_field.assignment_rule import get_assignment_rule_custom_fields
from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.custom.custom_field.hd_ticket import get_hd_ticket_custom_fields
from one_fm.custom.custom_field.attendance import get_attendance_custom_fields
from one_fm.custom.custom_field.todo import get_todo_custom_fields
from one_fm.custom.custom_field.scheduled_job_type import get_scheduled_job_type_custom_fields
from one_fm.custom.custom_field.task import get_task_custom_fields
# Property setter imports
from one_fm.custom.property_setter.assignment_rule import get_assignment_rule_properties
from one_fm.custom.property_setter.task import get_task_properties

def after_install():
	create_custom_fields(get_custom_fields())
	add_property_setter(get_field_properties())
	create_workflows()
	create_assignment_rules()
	frappe.db.commit()

def before_uninstall():
	delete_custom_fields(get_custom_fields())
	remove_property_setter(get_field_properties())
	delete_workflows()
	delete_assignment_rules()
	frappe.db.commit()

def get_custom_fields():
	"""ONEFM specific custom fields that need to be added to the masters in ERPNext"""
	custom_fields = get_additional_salary_custom_fields()
	custom_fields.update(get_supplier_group_custom_fields())
	custom_fields.update(get_assignment_rule_custom_fields())
	custom_fields.update(get_leave_type_custom_fields())
	custom_fields.update(get_employee_custom_fields())
	custom_fields.update(get_hd_ticket_custom_fields())
	custom_fields.update(get_attendance_custom_fields())
	custom_fields.update(get_todo_custom_fields())
	custom_fields.update(get_scheduled_job_type_custom_fields())
	custom_fields.update(get_task_custom_fields())
	return custom_fields

def add_property_setter(property_setters):
	for property in property_setters:
		make_property_setter(
			doctype=property.get("doc_type"),
			fieldname=property.get("field_name"),
			property=property.get("property"),
			value=property.get("value"),
			property_type=property.get("property_type"),
			for_doctype=property.get("doctype_or_field"),
			validate_fields_for_doctype=False
		)

def get_field_properties():
	"""ONEFM specific field properties that need to be added to the masters in ERPNext"""
	field_properties = get_assignment_rule_properties()
	field_properties.extend(get_task_properties())
	return field_properties

def create_workflows():
	create_workflow(get_workflow_json_file("erf.json"))
	create_workflow(get_workflow_json_file("leave_acknowledgement_form.json"))
	create_workflow(get_workflow_json_file("task.json"))

def create_assignment_rules():
	create_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
	create_assignment_rule(get_assignment_rule_json_file("subcontract_staff_shortlist.json"))
	create_assignment_rule(get_assignment_rule_json_file("action_poc_check.json"))
	create_assignment_rule(get_assignment_rule_json_file("shift_permission_approver.json"))
	create_assignment_rule(get_assignment_rule_json_file("task.json"))

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

def delete_workflows():
	delete_workflow(get_workflow_json_file("erf.json"))
	delete_workflow(get_workflow_json_file("leave_acknowledgement_form.json"))
	delete_workflow(get_workflow_json_file("task.json"))

def delete_assignment_rules():
	delete_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
	delete_assignment_rule(get_assignment_rule_json_file("subcontract_staff_shortlist.json"))
	delete_assignment_rule(get_assignment_rule_json_file("action_poc_check.json"))
	delete_assignment_rule(get_assignment_rule_json_file("shift_permission_approver.json"))
	delete_assignment_rule(get_assignment_rule_json_file("task.json"))
