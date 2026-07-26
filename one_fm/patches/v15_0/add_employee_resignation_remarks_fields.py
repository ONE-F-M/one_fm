import json

import frappe


def execute():
	"""Insert the new supervisor_remarks/operations_manager_remarks fields into
	Employee Resignation's field_order Property Setter (which overrides the
	DocType JSON's own field_order entirely -- see
	rebalance_employee_resignation_layout_single_employee for the same pattern):
	supervisor_remarks right after "supervisor", operations_manager_remarks
	right after "status" (first column of "More Information", alongside
	Offboarding Officer/Operations Manager rather than tucked under Operations
	Manager specifically in the third column).

	Idempotent and self-relocating: removes each fieldname from wherever it
	currently sits (in case this patch already ran with an earlier anchor)
	before re-inserting it at the correct position, so reruns always converge
	on the same layout regardless of the field's current position.
	"""
	frappe.reload_doc("one_fm", "doctype", "employee_resignation", force=True)

	ps_name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Employee Resignation", "property": "field_order", "field_name": ["is", "not set"]},
		"name",
	)
	if not ps_name:
		return

	ps = frappe.get_doc("Property Setter", ps_name)
	try:
		order = frappe.parse_json(ps.value)
	except Exception:
		return

	changed = False
	pairs = [("supervisor", "supervisor_remarks"), ("status", "operations_manager_remarks")]
	for anchor, new_field in pairs:
		if anchor not in order:
			continue
		if new_field in order:
			if order.index(new_field) == order.index(anchor) + 1:
				continue
			order.remove(new_field)
		order.insert(order.index(anchor) + 1, new_field)
		changed = True

	if changed:
		ps.value = json.dumps(order)
		ps.save()
		frappe.clear_cache(doctype="Employee Resignation")
