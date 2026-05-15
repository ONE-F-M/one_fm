import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields({
		"Employee": [
			{
				"depends_on": "eval:!doc.attendance_by_timesheet",
				"description": "If checked, the Employee is categorized as a Rambo reliever in Roster.",
				"fieldname": "custom_is_rambo_reliever",
				"fieldtype": "Check",
				"insert_after": "custom_is_weekend_reliever",
				"label": "Is Rambo Reliever",
			},
		]
	})

	# Update field_order property setter to include the new field
	ps_name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Employee", "property": "field_order"},
		"name",
	)
	if ps_name:
		ps = frappe.get_doc("Property Setter", ps_name)
		field_order = json.loads(ps.value)
		if "custom_is_rambo_reliever" not in field_order:
			idx = field_order.index("custom_is_weekend_reliever")
			field_order.insert(idx + 1, "custom_is_rambo_reliever")
			ps.value = json.dumps(field_order)
			ps.save(ignore_permissions=True)
