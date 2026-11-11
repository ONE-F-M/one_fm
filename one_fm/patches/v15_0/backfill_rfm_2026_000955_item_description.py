import frappe

from one_fm.purchase.doctype.request_for_material.request_for_material import (
	get_rfp_item_description,
)

PARENT = "Request for Material"
CHILD = "Request for Material Item"
NAME = "RFM-2026-000955"


def execute():
	"""HD-1925621: give RFM-2026-000955 the line descriptions its RFP needs.

	Both lines of this request, Choclates -Cacao and Empty Cards, carry a blank
	requested_description. `description` is mandatory on every Request for Purchase
	Item and was mapped straight off that field, so Create > Request for Purchase
	fails on the mandatory field and the Warehouse Supervisor cannot raise the
	purchase at all.

	He cannot fix it himself either: requested_description is not allow_on_submit, so
	it cannot be typed into the approved request, and the only way out was to cancel
	and amend a request that is already approved.

	get_rfp_item_description now falls back for every conversion from here on. This
	fills in the two lines already stranded behind the old mapping, taking the text
	from the same fallback the conversion uses, so the description is the one the RFP
	would have carried had the mapping been right.

	Other approved requests are left alone; they are a separate piece of work.
	"""
	if not frappe.db.exists(
		PARENT, {"name": NAME, "docstatus": 1, "workflow_state": "Approved"}
	):
		return

	rows = frappe.get_all(
		CHILD,
		filters={"parent": NAME, "parenttype": PARENT, "reject_item": 0},
		fields=[
			"name",
			"requested_description",
			"description",
			"requested_item_name",
			"item_name",
			"qty",
			"custom_rfp_quantity",
		],
	)

	for row in rows:
		if row.requested_description:
			continue

		# already converted in full, nothing left to raise a purchase for
		if (row.qty or 0) <= (row.custom_rfp_quantity or 0):
			continue

		description = get_rfp_item_description(row)
		if not description:
			continue

		# db.set_value, not the document: requested_description is not allow_on_submit,
		# so a save of the submitted parent would be refused.
		frappe.db.set_value(CHILD, row.name, "requested_description", description, update_modified=False)

	frappe.db.commit()
