import frappe


def execute():
	"""Clear Split From / Original Card on shipments whose target card was deleted.

	Older force deletes left these behind, and a full save of such a card fails with
	"Could not find Split From".
	"""
	doctype = "Transportation Shipment"
	existing = set(frappe.get_all(doctype, pluck="name"))
	for row in frappe.get_all(
		doctype,
		or_filters=[["split_parent", "is", "set"], ["split_root", "is", "set"]],
		fields=["name", "split_parent", "split_root"],
	):
		update = {
			field: None
			for field in ("split_parent", "split_root")
			if row[field] and row[field] not in existing
		}
		if update:
			frappe.db.set_value(doctype, row.name, update, update_modified=False)
