import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""Update the Overtime Request workflow and naming series."""
	# 1. Update the workflow
	create_workflow(get_workflow_json_file("overtime_request.json"))

	# 2. Update the naming series
	new_series = "OT-.MM.-.YYYY.-.####"

	# Remove existing Property Setters that override naming_series
	for ps in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Overtime Request", "field_name": "naming_series"},
		pluck="name"
	):
		frappe.delete_doc("Property Setter", ps, ignore_permissions=True)

	# Set the new naming series via Property Setter
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		"Overtime Request", "naming_series", "options", new_series, "Text"
	)
	make_property_setter(
		"Overtime Request", "naming_series", "default", new_series, "Text"
	)

	frappe.clear_cache(doctype="Overtime Request")
