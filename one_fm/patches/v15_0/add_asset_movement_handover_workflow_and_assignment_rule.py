import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.asset_movement import get_asset_movement_custom_fields
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)


def execute():
	"""Set up the Asset Movement handover: custom fields, workflow and assignment rule."""
	# 1. Add custom fields (Handover Employee User, Reason for Rejection)
	create_custom_fields(get_asset_movement_custom_fields())

	# 2. Create / update the Asset Movement workflow (Receive Asset / Reject Asset)
	create_workflow(get_workflow_json_file("asset_movement.json"))

	# 3. Create the assignment rule that routes the acceptance task to the To Employee
	create_assignment_rule(get_assignment_rule_json_file("asset_movement_employee.json"))
