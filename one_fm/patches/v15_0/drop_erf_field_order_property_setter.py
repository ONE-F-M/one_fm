"""WI-002316: let the ERF layout the app ships actually take effect.

Somebody reordered ERF through Customize Form at some point, which leaves a
Property Setter holding the whole field order. That setter overrides field_order in
erf.json, so the analyst's layout - which moves Employee Grade and Hiring Method out
of the HR section and up beside Reason for Request - had no effect on this site.

That is not cosmetic. The HR section only shows once the ERF is past initial review,
and both those fields are mandatory, so a new ERF demanded two fields it gave nobody
any way to fill.

The setter carries no customisation worth keeping: it is the app's own old order, and
it predates four fields the app ships (reports_to, reports_to_name, and the two the
analyst has just added), which is why they were being appended out of place.
"""

import frappe

BLOCKED_SECTION_MARKER = "workflow_state"


def execute():
	setters = frappe.get_all(
		"Property Setter",
		filters={"doc_type": "ERF", "doctype_or_field": "DocType", "property": "field_order"},
		pluck="name",
	)
	for name in setters:
		frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)

	frappe.clear_cache(doctype="ERF")

	# What the removal is for: no mandatory field may sit in a section that a new ERF
	# hides. A stale order puts one there without changing any field's own properties,
	# so nothing else in this app would notice.
	stranded = _mandatory_fields_a_new_erf_cannot_reach()
	if stranded:
		frappe.throw(
			"ERF still has mandatory fields a new ERF cannot reach: "
			+ ", ".join(f"{field} (under {section})" for field, section in stranded)
		)

	print(f"WI-002316: dropped {len(setters)} ERF field_order property setter(s)")


def _mandatory_fields_a_new_erf_cannot_reach() -> list:
	section = None
	stranded = []
	for field in frappe.get_meta("ERF").fields:
		if field.fieldtype == "Section Break":
			section = field
			continue
		if not field.reqd or field.hidden:
			continue
		hidden_by_section = bool(
			section is not None
			and section.depends_on
			and BLOCKED_SECTION_MARKER in section.depends_on
		)
		hidden_by_itself = bool(field.depends_on and BLOCKED_SECTION_MARKER in field.depends_on)
		if hidden_by_section or hidden_by_itself:
			stranded.append((field.fieldname, section.fieldname if section else None))
	return stranded
