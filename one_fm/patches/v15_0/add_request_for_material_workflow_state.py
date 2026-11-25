from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.request_for_material import get_request_for_material_custom_fields


def execute():
	# The Request for Material Lifecycle map sets workflow_state. Updates the field the old Workflow made, or adds it.
	create_custom_fields(get_request_for_material_custom_fields())
