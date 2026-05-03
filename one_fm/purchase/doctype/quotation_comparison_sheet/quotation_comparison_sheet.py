# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


class QuotationComparisonSheet(Document):
	def validate(self):
		self.validate_duplicate_item_awards()
		self.warn_partial_awards()
		self.recalculate_grand_total()

	def on_submit(self):
		if not self.items:
			frappe.throw(_("To submit the comparison sheet - Please fill the result to the items table"))
		update_request_for_purchase(self)

	def validate_duplicate_item_awards(self):
		"""Prevent the same item from being awarded to multiple suppliers."""
		if not self.items:
			return
		seen_items = {}
		for row in self.items:
			if not row.item_name:
				continue
			if row.item_name in seen_items:
				frappe.throw(
					_("Row #{0}: Item \"{1}\" has already been awarded in Row #{2}. "
					  "Please remove the existing selection before reassigning.").format(
						row.idx, row.item_name, seen_items[row.item_name]
					)
				)
			seen_items[row.item_name] = row.idx

	def warn_partial_awards(self):
		"""Warn if not all RFQ items have been assigned a supplier."""
		if not self.request_for_quotation or not self.items:
			return

		rfq_item_names = set()
		for qi in self.quotation_items or []:
			if qi.item_name:
				rfq_item_names.add(qi.item_name)

		awarded_item_names = set()
		for row in self.items:
			if row.item_name:
				awarded_item_names.add(row.item_name)

		missing = rfq_item_names - awarded_item_names
		if missing:
			frappe.msgprint(
				_("Warning: Not all requested items have been assigned a supplier. "
				  "The following items are un-sourced: {0}").format(
					", ".join(frappe.bold(name) for name in sorted(missing))
				),
				title=_("Partial Award"),
				indicator="orange"
			)

	def recalculate_grand_total(self):
		"""Recalculate grand_total from awarded items."""
		total = 0
		for row in self.items or []:
			total += (row.qty or 0) * (row.rate or 0)
		self.grand_total = total

	@frappe.whitelist()
	def get_rfq(self, rfq, rfm):
		return {
			"rfq": frappe.get_doc("Request for Quotation", rfq),
			"rfm": frappe.get_doc("Request for Material", rfm)
		}

	@frappe.whitelist()
	def sync_quotations(self):
		"""Append newly submitted Supplier Quotations to this Draft QCS
		without clearing existing selections."""
		if self.docstatus != 0:
			frappe.throw(_("Quotations can only be synced on a Draft QCS."))

		if not self.request_for_quotation:
			frappe.throw(_("Please select a Request for Quotation first."))

		# Get all Supplier Quotations linked to this RFQ
		all_quotations = frappe.get_list(
			"Supplier Quotation",
			filters={"custom_request_for_quotation": self.request_for_quotation},
			fields=["name"]
		)

		# Find existing quotation names in the table
		existing_quotation_names = set()
		for row in self.quotations or []:
			if row.quotation:
				existing_quotation_names.add(row.quotation)

		new_count = 0
		for sq_ref in all_quotations:
			if sq_ref.name in existing_quotation_names:
				continue

			sq = frappe.get_doc("Supplier Quotation", sq_ref.name)
			# Add to quotations table
			qtn = self.append("quotations")
			qtn.quotation = sq.name
			qtn.supplier = sq.supplier
			qtn.estimated_delivery_date = sq.valid_till
			qtn.grand_total = sq.grand_total

			# Add individual items to quotation_items table
			for item in sq.items:
				qi = self.append("quotation_items")
				qi.quotation = item.parent
				qi.quotation_item = item.name
				qi.item_name = item.item_name
				qi.description = item.description
				qi.estimated_delivery_date = sq.valid_till
				qi.quantity = item.qty
				qi.uom = item.uom
				qi.rate = item.rate
				qi.amount = item.amount
				qi.supplier = sq.supplier
				qi.supplier_name = sq.supplier_name
				qi.item_code = item.item_code

			new_count += 1

		if new_count > 0:
			self.save()
			frappe.msgprint(
				_("{0} new Supplier Quotation(s) synced successfully.").format(new_count),
				indicator="green"
			)
		else:
			frappe.msgprint(
				_("No new Supplier Quotations found. All are already included."),
				indicator="blue"
			)

		return new_count

	@frappe.whitelist()
	def create_purchase_order(self):
		"""Create Purchase Orders grouped by supplier from awarded items."""
		if self.docstatus != 1:
			frappe.throw(_("Purchase Orders can only be created from a submitted QCS."))

		if not self.items:
			frappe.throw(_("No items have been awarded. Please select items in the "
						   "'Choose Quotation and Supplier for Item' table before creating Purchase Orders."))

		# Separate awarded vs un-awarded items
		awarded_items = []
		skipped_items = []
		for row in self.items:
			if row.supplier:
				awarded_items.append(row)
			else:
				skipped_items.append(row)

		if not awarded_items:
			frappe.throw(_("No items have a supplier assigned. "
						   "Please select suppliers for items before creating Purchase Orders."))

		# Group by supplier
		suppliers = {}
		for item in awarded_items:
			supplier = item.supplier
			if supplier not in suppliers:
				suppliers[supplier] = []
			suppliers[supplier].append(item)

		# Get RFM for warehouse/schedule defaults
		rfm = None
		if self.request_for_material:
			rfm = frappe.get_doc("Request for Material", self.request_for_material)

		created_pos = []
		today = frappe.utils.today()
		for supplier, items in suppliers.items():
			po_items = []
			for i in items:
				item_schedule = i.schedule_date or i.estimated_delivery_date or self.required_date or today
				# Ensure schedule_date is not in the past (PO validates >= transaction_date)
				if str(item_schedule) < today:
					item_schedule = today
				po_item = {
					"item_code": i.item_code,
					"qty": i.qty,
					"rate": i.rate,
					"uom": i.uom,
					"schedule_date": item_schedule,
					"description": i.description,
				}
				po_items.append(po_item)

			po_schedule = self.required_date or (rfm.schedule_date if rfm else None) or today
			if str(po_schedule) < today:
				po_schedule = today

			po_doc = frappe.get_doc({
				"doctype": "Purchase Order",
				"supplier": supplier,
				"one_fm_request_for_purchase": self.request_for_purchase,
				"request_for_material": self.request_for_material,
				"custom_quotation_comparison_sheet": self.name,
				"schedule_date": po_schedule,
				"set_warehouse": rfm.target_warehouse if rfm else None,
				"items": po_items
			}).insert()
			created_pos.append(po_doc.name)

		# Show warning for skipped items
		if skipped_items:
			skipped_names = ", ".join(
				frappe.bold(row.item_name or "Row #{}".format(row.idx))
				for row in skipped_items
			)
			frappe.msgprint(
				_("Warning: The following items from the original RFM were left un-sourced "
				  "(no supplier selected) and were skipped: {0}").format(skipped_names),
				title=_("Items Skipped"),
				indicator="orange"
			)

		frappe.msgprint(
			_("{0} Purchase Order(s) created successfully: {1}").format(
				len(created_pos),
				", ".join(
					'<a href="/app/purchase-order/{0}">{0}</a>'.format(po)
					for po in created_pos
				)
			),
			title=_("Purchase Orders Created"),
			indicator="green"
		)

		return created_pos


def update_request_for_purchase(doc):
	if doc.items and doc.request_for_purchase:
		rfp = frappe.get_doc("Request for Purchase", doc.request_for_purchase)
		for item in doc.items:
			items_to_order = rfp.append("items_to_order")
			items_to_order.item_name = item.item_name
			items_to_order.description = item.description
			items_to_order.uom = item.uom
			items_to_order.qty_requested = item.qty
			items_to_order.qty = item.qty
			items_to_order.item_code = item.item_code
			items_to_order.t_warehouse = item.t_warehouse
			items_to_order.quotation = item.quotation
			items_to_order.quotation_item = item.quotation_item
			items_to_order.rate = frappe.db.get_value("Supplier Quotation Item", item.quotation_item, "rate")
			items_to_order.delivery_date = frappe.db.get_value("Supplier Quotation", item.quotation, "valid_till")
		rfp.save(ignore_permissions=True)


@frappe.whitelist()
def get_quotation_against_rfq(rfq):
	quotation_list = frappe.get_list(
		"Supplier Quotation",
		filters={"custom_request_for_quotation": rfq},
		fields=["name"]
	)
	quotations = []
	for quotation in quotation_list:
		quotations.append(frappe.get_doc("Supplier Quotation", quotation.name))
	return quotations
