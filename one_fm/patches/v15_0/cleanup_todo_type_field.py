import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.setup.custom_field import get_custom_fields


def execute():
	"""Update ToDo type field to Select with options and set non-Action records to Action."""

	# Step 1: Update the custom field from Data to Select with options
	create_custom_fields(get_custom_fields(), ignore_validate=True)

	# Step 2: Update all existing ToDos where type is not "Action" to "Action"
	frappe.db.set_value(
		"ToDo",
		{"type": ["not in", ["Action"]]},
		"type",
		"Action",
	)
