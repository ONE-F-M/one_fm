import json

import frappe


NEW_FIELD_ORDER = [
	"workflow_state", "resigning_employees_section",
	"employee", "resignation_letter", "employees",
	"designation", "resignation_initiation_date", "reason_for_exit",
	"column_break_twru", "department", "project_allocation", "site_allocation", "relieving_date",
	"column_break_pdtv", "employment_type", "shift_allocation", "operations_role_allocation",
	"section_break_xfjj", "full_name_in_english", "full_name_in_arabic",
	"nationality", "under_company_residency", "date_of_joining",
	"operational_impact_section", "supervisor", "replacement_required", "replacement_priority",
	"column_break_qfvv", "replacement_nationality", "replacement_gender",
	"column_break_visn", "replacement_salary", "ojt_days",
	"more_information_section", "status", "offboarding_officer",
	"column_break_jkbg", "naming_series",
	"column_break_bqiy", "amended_from", "shift_working", "operations_manager",
]


def execute():
	"""Reorder Employee Resignation's form to read: Employee first, then the
	site/allocation details as a balanced 3-column grid, with Resignation
	Initiation Date / Relieving Date folded into the bottom of columns 1 and 2
	(Designation + Initiation Date | Department/Project/Site Allocation +
	Relieving Date | Employment Type/Shift/Ops Role Allocation) -- all under a
	single "Resignation Details" heading (dropping the previous split between
	a "Resigning Employee" section and a second "Resignation Details" section
	that only ever held hidden fields). The dates used to need their own
	separate section to avoid the "employees" Table field misaligning
	sibling columns, but "employees" is hidden now, so that workaround is no
	longer needed and the dates can live in the same grid.

	Also moves OJT Days from the first "Operational Impact" column to the
	third, directly below Replacement Salary, and moves Replacement Priority
	from the third column to the first, directly below Is a Replacement
	Required?.

	Also makes resignation_letter allow_on_submit, so the attachment stays
	visible and editable for every role at every stage of the workflow instead
	of being locked once the document is submitted.

	Also places Reason for Exit directly below Resignation Initiation Date,
	at the bottom of column 1 (its box height is also capped via max_height
	on the field itself so it no longer dominates the column).

	Also removes the "Language and Skill Requirement" section (language_
	requirements, skill_requirements, certification_requirements) entirely --
	Project Manpower Request already has its own identical section for this,
	and Employee Resignation's copy only ever existed to pre-fill the PMR
	that gets auto-spawned on submit when a replacement is required. That
	pre-fill logic is removed from employee_resignation.py's on_submit() in
	the same change; the PMR now starts blank on these fields and whoever
	manages it fills them in directly there.

	This doctype's field_order is controlled by a live "field_order" Property
	Setter that takes precedence over the DocType JSON's own field_order --
	editing the JSON alone (even with a forced doctype reload) does not
	reorder already-existing fields, only updating that Property Setter's
	stored value does.
	"""
	frappe.reload_doc("one_fm", "doctype", "employee_resignation", force=True)

	ps_name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Employee Resignation", "property": "field_order", "field_name": ["is", "not set"]},
		"name",
	)

	if ps_name:
		ps = frappe.get_doc("Property Setter", ps_name)
		try:
			current_order = frappe.parse_json(ps.value)
		except Exception:
			current_order = None

		if current_order != NEW_FIELD_ORDER:
			ps.value = json.dumps(NEW_FIELD_ORDER)
			ps.save(ignore_permissions=True)
	else:
		frappe.get_doc({
			"doctype": "Property Setter",
			"doc_type": "Employee Resignation",
			"doctype_or_field": "DocType",
			"property": "field_order",
			"property_type": "Text",
			"value": json.dumps(NEW_FIELD_ORDER),
		}).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Employee Resignation")
