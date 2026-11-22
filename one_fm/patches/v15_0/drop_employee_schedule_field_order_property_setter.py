import frappe


def execute():
	"""Drop the Customize Form field_order setter so the Relieving Details layout in the JSON applies.

	The setter holds the app's old field order and pins is_relieving_schedule and
	relieving_employee_schedule under section_break_2, which leaves the new section empty.
	"""
	frappe.db.delete(
		"Property Setter",
		{"doc_type": "Employee Schedule", "doctype_or_field": "DocType", "property": "field_order"},
	)
	frappe.clear_cache(doctype="Employee Schedule")
