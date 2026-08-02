import json

import frappe


NEW_FIELD_ORDER = [
	"workflow_state", "resigning_employees_section", "employees",
	"resignation_dates_section", "resignation_initiation_date", "relieving_date",
	"section_break_xfjj", "employee", "full_name_in_english", "full_name_in_arabic",
	"nationality", "under_company_residency", "date_of_joining",
	"department", "employment_type", "designation",
	"column_break_twru", "project_allocation", "site_allocation",
	"column_break_pdtv", "shift_allocation", "operations_role_allocation",
	"operational_impact_section", "supervisor", "replacement_required", "ojt_days",
	"column_break_qfvv", "replacement_nationality", "replacement_gender",
	"column_break_visn", "replacement_salary", "replacement_priority",
	"section_break_tdav", "language_requirements", "skill_requirements", "certification_requirements",
	"more_information_section", "status", "offboarding_officer",
	"column_break_jkbg", "naming_series",
	"column_break_bqiy", "amended_from", "shift_working", "operations_manager",
]


def execute():
	"""Rebalance Employee Resignation's form layout, purely cosmetic (no data/behavior change):

	- Relieving Date now sits directly below Resignation Initiation Date, in the
	  same column, instead of side by side. This still needs its own new,
	  unlabeled Section Break (resignation_dates_section) placed right after the
	  "employees" Table field -- a Table field does not force a "row break" for
	  a section that follows it, so without this dedicated section the date
	  fields would render at the TOP of the next section, beside the Table,
	  instead of below it. Isolating the Table in its own single-column section
	  avoids this entirely.
	- The "Resignation Details" section previously rendered a large empty gap on
	  the left: its first column held only hidden lookup fields (employee,
	  full_name_in_english, full_name_in_arabic, nationality, under_company_residency,
	  date_of_joining), while the visible fields were unevenly split 3/4 across the
	  remaining two columns. Folded the hidden fields into the first visible column
	  and rebalanced the rest into a proper 3-column layout (3/2/2).
	- "Offboarding Officer" moved from the "More Information" section's third column
	  (stacked under Operations Manager) to its first column (next to Status).

	This doctype's field_order is controlled by a live "field_order" Property
	Setter that takes precedence over the DocType JSON's own field_order -- editing
	the JSON alone (and even a forced doctype reload) does not reorder existing
	fields, only the Property Setter's stored value is authoritative here.
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

		if current_order == NEW_FIELD_ORDER:
			return

		ps.value = json.dumps(NEW_FIELD_ORDER)
		ps.save()
	else:
		frappe.get_doc({
			"doctype": "Property Setter",
			"doc_type": "Employee Resignation",
			"doctype_or_field": "DocType",
			"property": "field_order",
			"property_type": "Text",
			"value": json.dumps(NEW_FIELD_ORDER),
		}).insert()

	frappe.clear_cache(doctype="Employee Resignation")
