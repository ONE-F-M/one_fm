import frappe
from frappe.query_builder.functions import Max

from one_fm.custom.client_script.employee_record_update_request import (
	get_employee_record_update_request_client_scripts,
)
from one_fm.patches.v15_0.processa_sync_employee_record_update_request___v1_9c10e5 import add_client_script

REQUEST = "Employee Record Update Request"
TERMS_ITEM = "Employee Record Update Request Properties Item"
BENEFITS_ITEM = "Employee Record Update Request Benefits Item"
# Not on the BA site; day-off changes use the Day Off Terms section.
REMOVED_PROPERTIES = ("Number of Days Off", "Day Off Category")


def execute():
	copy_property_to_terms(TERMS_ITEM)
	copy_property_to_terms(BENEFITS_ITEM)
	rename_car_benefit()
	move_properties_rows()
	remove_day_off_properties()
	add_client_script(get_employee_record_update_request_client_scripts())


def copy_property_to_terms(doctype):
	"""The `property` column is orphaned by migrate; copy it into `terms` where terms is empty."""
	if not frappe.db.has_column(doctype, "property"):
		return
	table = frappe.qb.DocType(doctype)
	(
		frappe.qb.update(table)
		.set(table.terms, table.property)
		.where((table.terms.isnull() | (table.terms == "")) & table.property.isnotnull())
	).run()


def rename_car_benefit():
	table = frappe.qb.DocType(BENEFITS_ITEM)
	frappe.qb.update(table).set(table.terms, "Company Car").where(table.terms == "Car").run()


def move_properties_rows():
	"""Rows of the removed Properties table move to Employment Terms on requests that had it ticked."""
	if not frappe.db.has_column(REQUEST, "properties_changes_required"):
		return
	request = frappe.qb.DocType(REQUEST)
	parents = (
		frappe.qb.from_(request).select(request.name).where(request.properties_changes_required == 1)
	).run(pluck=True)
	if not parents:
		return

	item = frappe.qb.DocType(TERMS_ITEM)
	in_scope = (item.parenttype == REQUEST) & item.parent.isin(parents)
	rows = (
		frappe.qb.from_(item)
		.select(item.name, item.parent)
		.where(in_scope & (item.parentfield == "properties"))
		.orderby(item.parent)
		.orderby(item.idx)
	).run(as_dict=True)
	last_idx = dict(
		(
			frappe.qb.from_(item)
			.select(item.parent, Max(item.idx))
			.where(in_scope & (item.parentfield == "employment_terms"))
			.groupby(item.parent)
		).run()
	)
	for row in rows:
		last_idx[row.parent] = (last_idx.get(row.parent) or 0) + 1
		frappe.db.set_value(
			TERMS_ITEM,
			row.name,
			{"parentfield": "employment_terms", "idx": last_idx[row.parent]},
			update_modified=False,
		)

	frappe.qb.update(request).set(request.term_changes_required, 1).where(request.name.isin(parents)).run()
	frappe.qb.update(request).set(request.properties_changes_required, 0).where(request.name.isin(parents)).run()
	print(f"Moved {len(rows)} Properties rows to Employment Terms on {len(parents)} requests")


def remove_day_off_properties():
	for name in REMOVED_PROPERTIES:
		if frappe.db.exists("Record Update Property", name):
			frappe.delete_doc("Record Update Property", name, force=True, ignore_permissions=True)
