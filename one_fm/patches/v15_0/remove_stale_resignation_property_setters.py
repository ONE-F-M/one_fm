import frappe


def execute():
	"""A "Customize Form"-style Property Setter overriding Employee
	Resignation's field_order has been silently overriding every field_order
	change made to the doctype JSON throughout the v2 redesign -- its stored
	snapshot predates the redesign entirely (it still references the
	operations_manager field, deleted at the very start of this branch, and
	is missing every field added since). Property Setters take precedence
	over the doctype JSON's own field_order, so none of those layout changes
	were ever actually visible. Also drops an orphaned Property Setter for
	operations_manager's mandatory_depends_on, since that field no longer
	exists.
	"""
	frappe.delete_doc(
		"Property Setter", "Employee Resignation-main-field_order",
		ignore_missing=True,
	)
	frappe.delete_doc(
		"Property Setter", "Employee Resignation-operations_manager-mandatory_depends_on",
		ignore_missing=True,
	)
	frappe.clear_cache(doctype="Employee Resignation")
