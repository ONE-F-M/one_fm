"""Grade belongs on the Salary tab, not Government Relation.

Layout only - the field itself is untouched, so nothing that reads or writes Grade changes.
It is a standard HRMS field whose stock home IS the salary section; this app's field_order
had moved it under Government Relation, and this puts it back.

add_property_setter rewrites the whole Employee field_order, which is the only way to move
one field: the order is a single stored list, not a per-field property.
"""

import frappe

from one_fm.custom.property_setter.employee import get_employee_properties
from one_fm.setup.setup import add_property_setter

DOCTYPE = "Employee"
FIELD = "grade"
AFTER = "salary_information"


def execute():
	add_property_setter(get_employee_properties())
	move_in_doctype_layouts()


def move_in_doctype_layouts():
	"""Apply the same move to any DocType Layout on Employee.

	A DocType Layout registers a route under its own slugged name, so a layout called
	"Employee" takes over /app/employee and the form renders from the layout's stored
	field list instead of the doctype's field_order. Property Setter never touches a
	layout, and DocTypeLayout.sync_fields only adds and removes fields - neither reorders
	one - so without this the field_order above is written and never seen.
	"""
	for name in frappe.get_all(
		"DocType Layout", filters={"document_type": DOCTYPE}, pluck="name"
	):
		layout = frappe.get_doc("DocType Layout", name)

		row = next((f for f in layout.fields if f.fieldname == FIELD), None)
		anchor = next((f for f in layout.fields if f.fieldname == AFTER), None)
		if not row or not anchor or row.idx == anchor.idx + 1:
			continue

		layout.fields.remove(row)
		layout.fields.insert(layout.fields.index(anchor) + 1, row)
		for index, field in enumerate(layout.fields):
			field.idx = index + 1

		layout.save(ignore_permissions=True)

	frappe.clear_cache(doctype=DOCTYPE)
