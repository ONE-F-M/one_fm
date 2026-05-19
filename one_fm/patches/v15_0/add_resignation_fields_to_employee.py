import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	create_custom_fields({
		"Employee": [
			{
				"fetch_from": "current_resignation.workflow_state",
				"fieldname": "resignation_status",
				"fieldtype": "Data",
				"insert_after": "feedback",
				"is_system_generated": 1,
				"label": "Resignation Workflow Status",
				"read_only": 1,
			},
			{
				"fieldname": "current_resignation",
				"fieldtype": "Link",
				"hidden": 1,
				"insert_after": "resignation_status",
				"is_system_generated": 1,
				"label": "Current Resignation",
				"options": "Employee Resignation",
				"read_only": 1,
			},
			{
				"label": "Current Withdrawal",
				"fieldname": "current_withdrawal",
				"insert_after": "current_resignation",
				"fieldtype": "Link",
				"options": "Employee Resignation Withdrawal",
				"is_system_generated": 1
			},
			{
				"label": "Resignation Status & Documents",
				"fieldname": "resignation_section",
				"insert_after": "feedback",
				"fieldtype": "Section Break",
				"is_system_generated": 1
			},
			{
				"label": "Resignation Date",
				"fieldname": "resignation_date",
				"insert_after": "date_of_joining",
				"fieldtype": "Date",
				"read_only": 1,
				"is_system_generated": 1
			}
		]
	})
