import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add custom_accommodation_checked_out field to Leave Application and update
	the 'Leave Application - Approved' assignment rule's unassign_condition.

	The old condition used frappe.db.exists() which is not available in safe_eval.
	The new condition checks the custom_accommodation_checked_out field instead.
	"""
	# Step 1: Create the custom field
	create_custom_fields({
		"Leave Application": [
			{
				"fieldname": "custom_accommodation_checked_out",
				"fieldtype": "Check",
				"insert_after": "custom_in_accommodation",
				"label": "Accommodation Checked Out",
				"read_only": 1,
				"hidden": 1,
				"allow_on_submit": 1,
				"description": "Set automatically when an OUT Accommodation Leave Movement is submitted",
			}
		]
	})

	# Step 2: Update the assignment rule's unassign_condition
	rule_name = "Leave Application - Approved"
	if frappe.db.exists("Assignment Rule", rule_name):
		frappe.db.set_value(
			"Assignment Rule",
			rule_name,
			"unassign_condition",
			'custom_accommodation_checked_out == 1',
		)
		frappe.clear_cache(doctype="Assignment Rule")
