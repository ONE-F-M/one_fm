import frappe
import json
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cint, cstr, flt, get_link_to_form
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.party import get_party_account
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules
from one_fm.purchase.doctype.request_for_purchase.request_for_purchase import update_rfp_status
from frappe.utils import nowdate


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None, args=None):
    if args is None:
        args = {}
    if isinstance(args, str):
        args = json.loads(args)

    has_unit_price_items = frappe.db.get_value("Purchase Order", source_name, "has_unit_price_items")

    def is_unit_price_row(source):
        return has_unit_price_items and source.qty == 0

    def update_item(obj, target, source_parent):
        remaining_qty = flt(obj.qty) - flt(obj.received_qty)
        
        if is_unit_price_row(obj):
            target.qty = flt(obj.qty)
        elif remaining_qty > 0:
            target.qty = remaining_qty
        else:
            target.qty = flt(obj.qty)
        
        target.stock_qty = target.qty * flt(obj.conversion_factor)
        target.amount = target.qty * flt(obj.rate)
        target.base_amount = target.amount * flt(source_parent.conversion_rate)


    def select_item(d):
        filtered_items = args.get("filtered_children", [])
        child_filter = d.name in filtered_items if filtered_items else True
        return child_filter
    
    doc = get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Purchase Receipt",
                "field_map": {
                    "supplier_warehouse": "supplier_warehouse",
                    "custom_customer": "custom_customer",
                    "project": "project",
                    "custom_site": "custom_site",
                    "is_refundable": "custom_refundable",
                    "one_fm_request_for_purchase": "custom_request_for_purchase",
                    "request_for_material": "custom_request_for_material",
                    "custom_margin_type": "custom_margin_type",
                    "custom_margin_rate_or_amount": "custom_margin_rate_or_amount",
                    "base_grand_total": "base_grand_total",
                    "base_net_total": "base_net_total",
                },
                "validation": {
                    "docstatus": ["=", 1],
                },
            },
            "Purchase Order Item": {
                "doctype": "Purchase Receipt Item",
                "field_map": {
                    "name": "purchase_order_item",
                    "parent": "purchase_order",
                    "bom": "bom",
                    "material_request": "material_request",
                    "material_request_item": "material_request_item",
                    "sales_order": "sales_order",
                    "sales_order_item": "sales_order_item",
                    "wip_composite_asset": "wip_composite_asset",
                    "is_refundable": "custom_refundable",
                    "margin_type": "margin_type",
                    "margin_rate_or_amount": "margin_rate_or_amount",
                    "rate_with_margin": "rate_with_margin",
                },
                "postprocess": update_item,
                "condition": lambda doc: (
                    True if is_unit_price_row(doc) else abs(doc.received_qty) < abs(doc.qty)
                )
                and doc.delivered_by_supplier != 1
                and select_item(doc),
            },
            "Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "reset_value": True},
        },
        target_doc,
        set_missing_values,
    )


    return doc


def set_missing_values(source, target):
    if source.get("one_fm_request_for_purchase"):
        target.custom_request_for_purchase = source.get("one_fm_request_for_purchase")
    if source.get('request_for_material'):
        target.custom_request_for_material = source.get('request_for_material')
    target.run_method("set_missing_values")
    target.run_method("calculate_taxes_and_totals")
    target.run_method("set_use_serial_batch_fields")
    target.save()
    


def set_workflow_states(doc,old_doc):
    """Sets approval dates based on workflow state changes."""
    current_workflow_state = doc.workflow_state

    # If the workflow state didn't change, no action is needed
    if old_doc.workflow_state == current_workflow_state:
        return

    # Mapping workflow states to custom field names
    workflow_mapping = {
        "Pending Purchase Manager": "custom_purchase_officer_approval_date",
        "Pending Finance Approver": "custom_purchase_manager_approval_date",
    }

    # Set approval dates based on current workflow state
    if current_workflow_state in workflow_mapping:
        doc.db_set(workflow_mapping[current_workflow_state],nowdate())



def on_update(doc, event):
    """Handles the update event for the Purchase Order document."""
    #Check if workflow_state was changed, if it wasn't then we return,
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return
    if old_doc.workflow_state == doc.workflow_state:
        return
    # Check if both dates are present; if so, no action is needed.
    if doc.custom_purchase_officer_approval_date and doc.custom_purchase_manager_approval_date:
        return
    set_workflow_states(doc,old_doc)
    
    
def validate_purchase_uom(doc, method):
    for item in doc.items:
        if item.conversion_factor:
            continue

        query = """
            select
                uom
            from
                `tabUOM Conversion Detail`
            where
                parent = %s
        """
        uoms_list = frappe.db.sql(
            query,
            item.item_code,
            as_list=True,
        )
        uoms = [item for sublist in uoms_list for item in sublist]
        if uoms and len(uoms) > 0:
            if item.uom not in uoms:
                msg = "The selected UOM in the row {0} is not having any UOM conversion Details in the item {1}".format(item.idx, item.item_code)
                frappe.throw(_(msg))

@frappe.whitelist()
def filter_purchase_uoms(doctype, txt, searchfield, start, page_len, filters):
    # filter UOM in item lines by UOM Conversion Detail set in the item
	query = """
		select
            uom
        from
            `tabUOM Conversion Detail`
        where
            parent = %(item_code)s
			and uom like %(txt)s
			limit %(start)s, %(page_len)s"""
	return frappe.db.sql(query,
		{
			'item_code': filters.get("item_code"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)

class PurchaseOrderOverride(PurchaseOrder):  

    def validate(self):
        super(PurchaseOrderOverride, self).validate()
        if self.request_for_material and not self.one_fm_request_for_purchase:
            frappe.throw(_("Request for Purchase is required for this Purchase Order to be processed further"))

    def on_submit(self):
        self.update_purchased_quantities()
        self.update_ordered_and_pending_quantities()
        if self.one_fm_request_for_purchase:
            update_rfp_status(self.one_fm_request_for_purchase)
    
    def on_update_after_submit(self):
        self.update_purchased_quantities()
        self.update_ordered_and_pending_quantities()
        if self.one_fm_request_for_purchase:
            update_rfp_status(self.one_fm_request_for_purchase)

    def on_cancel(self):
        self.update_purchased_quantities()
        self.update_ordered_and_pending_quantities()
        if self.one_fm_request_for_purchase:
            update_rfp_status(self.one_fm_request_for_purchase)


    def update_purchased_quantities(self):
        if not self.one_fm_request_for_purchase:
            return

        purchase_orders = frappe.db.get_list(
            "Purchase Order", 
            filters={"one_fm_request_for_purchase": self.one_fm_request_for_purchase, "docstatus": 1},
            pluck='name'
        )

        request_for_material = frappe.db.get_value(
            "Request for Purchase", 
            {"name": self.one_fm_request_for_purchase},
            "request_for_material"
        )

        for obj in self.items:
            po_items = frappe.db.get_all(
                "Purchase Order Item",
                filters={
                    "parent": ["in", purchase_orders], 
                    "item_code": obj.item_code, 
                    "parentfield": "items"
                },
                fields=["stock_qty", "qty", "uom", "stock_uom", "conversion_factor"]
            )
            
            total_purchased_stock_qty = 0
            for po_item in po_items:
                if po_item.stock_qty and po_item.stock_qty > 0:
                    total_purchased_stock_qty += po_item.stock_qty
                elif po_item.uom and po_item.stock_uom and po_item.uom != po_item.stock_uom and po_item.conversion_factor:
                    total_purchased_stock_qty += (po_item.qty or 0) * (po_item.conversion_factor or 1)
                else:
                    total_purchased_stock_qty += po_item.qty or 0
            
            update_purchased_qty(
                total_purchased_stock_qty, 
                self.one_fm_request_for_purchase, 
                obj.item_code, 
                "Request for Purchase Item", 
                "purchased_quantity"
            )

            if request_for_material:
                update_purchased_qty(
                    total_purchased_stock_qty, 
                    request_for_material, 
                    obj.item_code, 
                    "Request for Material Item", 
                    "ordered_qty"
                )
            

    def update_ordered_and_pending_quantities(self):
        if not self.one_fm_request_for_purchase:
            return

        purchase_orders = frappe.db.get_list(
            "Purchase Order", 
            filters={"one_fm_request_for_purchase": self.one_fm_request_for_purchase, "docstatus": 1},
            pluck='name'
        )

        rfp_items = frappe.db.get_all(
            "Request for Purchase Quotation Item",
            filters={"parent": self.one_fm_request_for_purchase},
            fields=["name", "item_code", "qty", "stock_qty", "uom", "stock_uom", "conversion_factor"]
        )

        for rfp_item in rfp_items:
            po_items = frappe.db.get_all(
                "Purchase Order Item", 
                filters={
                    "parent": ["in", purchase_orders], 
                    "item_code": rfp_item.item_code, 
                    "parentfield": "items"
                },
                fields=["stock_qty", "qty", "uom", "stock_uom", "conversion_factor"]
            )
            
            total_ordered_stock_qty = 0
            for po_item in po_items:
                if po_item.stock_qty:
                    total_ordered_stock_qty += po_item.stock_qty
                elif po_item.uom and po_item.stock_uom and po_item.uom != po_item.stock_uom:
                    conversion_factor = po_item.conversion_factor or 1
                    total_ordered_stock_qty += (po_item.qty or 0) * conversion_factor
                else:
                    total_ordered_stock_qty += po_item.qty or 0
            
            rfp_qty_in_stock_uom = rfp_item.stock_qty if rfp_item.stock_qty else rfp_item.qty
            pending_qty = max(0, rfp_qty_in_stock_uom - total_ordered_stock_qty)
            
            frappe.db.set_value(
                "Request for Purchase Quotation Item", 
                rfp_item.name, 
                {
                    "ordered_qty": total_ordered_stock_qty,
                    "pending_qty": pending_qty
                }
            )

        frappe.db.commit()  



def update_purchased_qty(new_qty, parent, item_code, doctype, qty_field):
    frappe.db.sql(
        f"""
        UPDATE `tab{doctype}`
        SET {qty_field} = %s
        WHERE parenttype = %s
        AND parent = %s
        AND item_code = %s
        """,
        (new_qty, doctype.replace(" Item", ""), parent, item_code),
    )



def calculate_margin(doc, item):
	rate_with_margin = 0.0
	base_rate_with_margin = 0.0
	
	if item.get("is_refundable"):
		rate_with_margin = item.rate or item.price_list_rate or 0
		base_rate_with_margin = flt(rate_with_margin * doc.doc.conversion_rate)
		return rate_with_margin, base_rate_with_margin
	
	if item.price_list_rate:
		if item.pricing_rules and not doc.doc.ignore_pricing_rule:
			has_pricing_rule_margin = False
			for d in get_applied_pricing_rules(item.pricing_rules):
				pricing_rule = frappe.get_cached_doc("Pricing Rule", d)

				if pricing_rule.margin_rate_or_amount and (
					(
						pricing_rule.currency == doc.doc.currency
						and pricing_rule.margin_type in ["Amount", "Percentage"]
					)
					or pricing_rule.margin_type == "Percentage"
				):
					margin_value = (
						pricing_rule.margin_rate_or_amount
						if pricing_rule.margin_type == "Amount"
						else flt(item.price_list_rate) * flt(pricing_rule.margin_rate_or_amount) / 100
					)
					rate_with_margin = flt(item.price_list_rate) + flt(margin_value)
					base_rate_with_margin = flt(rate_with_margin) * flt(doc.doc.conversion_rate)
					has_pricing_rule_margin = True
					break

			if has_pricing_rule_margin:
				return rate_with_margin, base_rate_with_margin

		if not item.pricing_rules and flt(item.rate) > flt(item.price_list_rate):
			item.rate_with_margin = item.rate

		if item.margin_type and item.margin_rate_or_amount:
			margin_value = (
				item.margin_rate_or_amount
				if item.margin_type == "Amount"
				else flt(item.price_list_rate) * flt(item.margin_rate_or_amount) / 100
			)
			rate_with_margin = flt(item.price_list_rate) + flt(margin_value)
			base_rate_with_margin = flt(rate_with_margin) * flt(doc.doc.conversion_rate)

	return rate_with_margin, base_rate_with_margin



@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	return get_mapped_purchase_invoice(source_name, target_doc, args=args)



def get_mapped_purchase_invoice(source_name, target_doc=None, ignore_permissions=False, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def postprocess(source, target):
		target.flags.ignore_permissions = ignore_permissions
		set_missing_values(source, target)

		# set tax_withholding_category from Purchase Order
		if source.apply_tds and source.tax_withholding_category and target.apply_tds:
			target.tax_withholding_category = source.tax_withholding_category

		# Get the advance paid Journal Entries in Purchase Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

		target.set_payment_schedule()
		target.credit_to = get_party_account("Supplier", source.supplier, source.company)

	def update_item(obj, target, source_parent):
		def get_billed_qty(po_item_name):

			table = frappe.qb.DocType("Purchase Invoice Item")
			query = (
				frappe.qb.from_(table)
				.select(Sum(table.qty).as_("qty"))
				.where((table.docstatus == 1) & (table.po_detail == po_item_name))
			)
			return query.run(pluck="qty")[0] or 0

		billed_qty = flt(get_billed_qty(obj.name))
		target.qty = flt(obj.qty) - billed_qty

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)
		target.cost_center = (
			obj.cost_center
			or frappe.db.get_value("Project", obj.project, "cost_center")
			or item.get("buying_cost_center")
			or item_group.get("buying_cost_center")
		)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	fields = {
		"Purchase Order": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"supplier_warehouse": "supplier_warehouse",
                "is_refundable": "custom_refundable",
			},
			"field_no_map": ["payment_terms_template"],
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Purchase Order Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"name": "po_detail",
				"parent": "purchase_order",
				"material_request": "material_request",
				"material_request_item": "material_request_item",
				"wip_composite_asset": "wip_composite_asset",
                "is_refundable": "custom_refundable"
			},
			"postprocess": update_item,
			"condition": lambda doc: (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount))
			and select_item(doc),
		},
		"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges", "reset_value": True},
	}

	doc = get_mapped_doc(
		"Purchase Order",
		source_name,
		fields,
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	return doc
