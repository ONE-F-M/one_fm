import json

import frappe


def execute():
	"""Insert the new supervisor_remarks/operations_manager_remarks fields into
	Employee Resignation's field_order Property Setter (which overrides the
	DocType JSON's own field_order entirely -- see
	rebalance_employee_resignation_layout_single_employee for the same pattern),
	right after "supervisor" and "operations_manager" respectively.

	Additive only: inserts each fieldname only if it's missing, leaving
	everything else in the stored order untouched.
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
	pairs = [("supervisor", "supervisor_remarks"), ("operations_manager", "operations_manager_remarks")]
	for anchor, new_field in pairs:
		if new_field in order:
			continue
		if anchor not in order:
			continue
		order.insert(order.index(anchor) + 1, new_field)
		changed = True

	if changed:
		ps.value = json.dumps(order)
		ps.save()
		frappe.clear_cache(doctype="Employee Resignation")
