import json

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class PurchaseInvoiceOverride(PurchaseInvoice):

    def validate(self):
        super().validate()
        self.validate_purchase_receipt_required()

    def validate_purchase_receipt_required(self):
        if not self.items:
            return
        
        has_purchase_receipt = any(item.purchase_receipt for item in self.items)
        
        if not has_purchase_receipt:
            frappe.throw("Purchase Invoice must be created from a submitted Purchase Receipt.")

            
    
    def on_submit(self):
        super(PurchaseInvoiceOverride, self).on_submit()
        if self.custom_refundable:
            self.initialize_pending_si_quantities()
    
    def on_cancel(self):
        self.validate_no_linked_sales_invoices()
        super(PurchaseInvoiceOverride, self).on_cancel()
    
    def initialize_pending_si_quantities(self):
        for item in self.items:
            frappe.db.set_value(
                "Purchase Invoice Item",
                item.name,
                "custom_pending_si_quantity",
                item.qty,
                update_modified=False
            )
    
    def validate_no_linked_sales_invoices(self):
        linked_sales_invoices = frappe.db.sql("""
            SELECT DISTINCT si.name
            FROM `tabSales Invoice` si
            INNER JOIN `tabSales Invoice Item` si_item ON si_item.parent = si.name
            WHERE si.docstatus = 1
            AND si_item.custom_purchase_invoice = %s
        """, (self.name), as_dict=1)
        
        if linked_sales_invoices:
            si_list = ", ".join([d.name for d in linked_sales_invoices])
            frappe.throw(
                _("Cannot cancel Purchase Invoice {0} as it is linked to submitted Sales Invoice(s): {1}").format(
                    self.name, si_list
                )
            )




@frappe.whitelist()
def get_all_refundable_purchase_invoices():
    invoices = frappe.db.sql("""
        SELECT DISTINCT
            pi.name,
            pi.posting_date,
            pi.supplier,
            pi.custom_customer as customer,
            pi.project,
            pi.custom_site as site,
            pi.currency
        FROM 
            `tabPurchase Invoice` pi
        INNER JOIN
            `tabPurchase Invoice Item` pii ON pii.parent = pi.name
        WHERE 
            pi.docstatus = 1 
            AND pi.custom_refundable = 1
            AND pii.custom_pending_si_quantity > 0
        ORDER BY 
            pi.posting_date DESC
    """, as_dict=1)
    
    return invoices


@frappe.whitelist()
def make_sales_invoice_from_purchase_invoice(source_names, target_doc=None):
    if isinstance(source_names, str):
        source_names = json.loads(source_names)
    
    if not isinstance(source_names, list):
        source_names = [source_names]
    
    validate_purchase_invoices(source_names)
    
    first_pi = frappe.get_doc("Purchase Invoice", source_names[0])
    
    if isinstance(target_doc, str):
        target_doc = frappe.get_doc(json.loads(target_doc))
    elif not target_doc:
        target_doc = frappe.new_doc("Sales Invoice")
    
    if not target_doc.get("company"):
        target_doc.company = first_pi.company
    
    if not target_doc.get("posting_date"):
        target_doc.posting_date = first_pi.posting_date
    
    if not target_doc.get("customer"):
        target_doc.customer = first_pi.get("custom_customer")
    
    if not target_doc.get("project"):
        target_doc.project = first_pi.get("project")
    
    if not target_doc.get("custom_site"):
        target_doc.custom_site = first_pi.get("custom_site")
    
    if not target_doc.get("custom_purchase_invoice"):
        target_doc.custom_purchase_invoice = source_names[0] if len(source_names) == 1 else None
    
    target_doc.custom_margin_type = first_pi.custom_margin_type
    target_doc.custom_margin_rate_or_amount = first_pi.custom_margin_rate_or_amount
    target_doc.custom_refundable = first_pi.custom_refundable
    
    company_currency = frappe.get_cached_value("Company", target_doc.company, "default_currency")
    
    for pi_name in source_names:
        pi_doc = frappe.get_doc("Purchase Invoice", pi_name)
        
        if not target_doc.get("currency"):
            target_doc.currency = pi_doc.currency
        
        currency_changed = pi_doc.currency != target_doc.currency
        
        if currency_changed:
            exchange_rate = get_exchange_rate(
                pi_doc.currency,
                target_doc.currency,
                target_doc.posting_date,
                "for_selling"
            )
        else:
            exchange_rate = 1.0
        
        if target_doc.currency != company_currency and not target_doc.get("conversion_rate"):
            target_doc.conversion_rate = get_exchange_rate(
                target_doc.currency,
                company_currency,
                target_doc.posting_date,
                "for_selling"
            )
        
        for pi_item in pi_doc.items:
            remaining_qty = get_remaining_qty_to_bill(pi_item)
            
            if remaining_qty > 0:
                si_item = target_doc.append("items", {})
                si_item.item_code = pi_item.item_code
                si_item.item_name = pi_item.item_name
                si_item.description = pi_item.description
                
                si_item.qty = remaining_qty
                si_item.uom = pi_item.uom
                si_item.conversion_factor = pi_item.conversion_factor or 1.0
                si_item.stock_uom = pi_item.stock_uom
                si_item.stock_qty = remaining_qty * flt(pi_item.conversion_factor or 1.0)
                
                if currency_changed:
                    calculated_rate = flt(pi_item.rate) * flt(exchange_rate)
                else:
                    calculated_rate = pi_item.rate
                
                si_item.rate = calculated_rate
                
                price_list_rate_value = pi_item.get("price_list_rate") or 0
                if price_list_rate_value == 0:
                    si_item.price_list_rate = calculated_rate
                else:
                    if currency_changed:
                        si_item.price_list_rate = flt(price_list_rate_value) * flt(exchange_rate)
                    else:
                        si_item.price_list_rate = price_list_rate_value
                
                si_item.amount = flt(si_item.qty) * flt(si_item.rate)
                si_item.base_rate = flt(si_item.rate) * flt(target_doc.conversion_rate or 1)
                si_item.base_amount = flt(si_item.amount) * flt(target_doc.conversion_rate or 1)
                si_item.base_price_list_rate = flt(si_item.price_list_rate) * flt(target_doc.conversion_rate or 1)
                
                if si_item.stock_qty:
                    si_item.stock_uom_rate = flt(si_item.amount) / flt(si_item.stock_qty)
                else:
                    si_item.stock_uom_rate = si_item.rate
                
                si_item.net_rate = si_item.rate
                si_item.net_amount = si_item.amount
                si_item.base_net_rate = si_item.base_rate
                si_item.base_net_amount = si_item.base_amount
                
                si_item.warehouse = pi_item.get("warehouse")
                si_item.cost_center = pi_item.cost_center
                si_item.project = pi_item.get("project")
                
                si_item.margin_type = pi_item.get("margin_type") or ""
                si_item.margin_rate_or_amount = flt(pi_item.get("margin_rate_or_amount") or 0)
                si_item.rate_with_margin = flt(pi_item.get("rate_with_margin") or 0)
                si_item.custom_refundable = pi_item.get("custom_refundable")
                si_item.base_rate_with_margin = flt(si_item.rate_with_margin) * flt(target_doc.conversion_rate or 1)
                
                si_item.discount_percentage = flt(pi_item.get("discount_percentage") or 0)
                si_item.discount_amount = flt(pi_item.get("discount_amount") or 0)
                
                si_item.item_tax_rate = pi_item.get("item_tax_rate") or json.dumps({}) 
                si_item.price_list_rate = flt(si_item.price_list_rate or si_item.rate or 0)  
                si_item.discount_percentage = flt(si_item.discount_percentage or 0)
                si_item.discount_amount = flt(si_item.discount_amount or 0)
 
                si_item.custom_purchase_invoice = pi_name
                si_item.custom_purchase_invoice_item = pi_item.name
                si_item.custom_pi_currency = pi_doc.currency
                si_item.custom_pi_exchange_rate = exchange_rate if currency_changed else 1.0
                si_item.custom_contract_item_category = frappe.db.get_value("Item", pi_item.item_code, "subitem_group")

    
    target_doc.run_method("set_missing_values")
    target_doc.run_method("calculate_taxes_and_totals")
    
    return target_doc

def validate_purchase_invoices(source_names):
    if not source_names:
        frappe.throw(_("Please select at least one Purchase Invoice"))
    
    pi_docs = []
    validation_errors = []
    
    for name in source_names:
        pi = frappe.get_doc("Purchase Invoice", name)
        
        if pi.docstatus != 1:
            validation_errors.append(_("Purchase Invoice {0} is not submitted").format(name))
            continue
        
        if not pi.get("custom_refundable"):
            validation_errors.append(_("Purchase Invoice {0} is not marked as refundable").format(name))
            continue
        
        has_remaining_qty = False
        for item in pi.items:
            if get_remaining_qty_to_bill(item) > 0:
                has_remaining_qty = True
                break
        
        if not has_remaining_qty:
            validation_errors.append(_("Purchase Invoice {0} has no remaining quantity to bill").format(name))
            continue
        
        pi_docs.append(pi)
    
    if validation_errors:
        frappe.throw("<br>".join(validation_errors))
    
    if len(pi_docs) > 1:
        first_pi = pi_docs[0]
        first_customer = first_pi.get("custom_customer")
        first_project = first_pi.get("project")
        first_site = first_pi.get("custom_site")
        
        different_customer = False
        different_project = False
        different_site = False
        
        for pi in pi_docs[1:]:
            if pi.get("custom_customer") != first_customer:
                different_customer = True
            
            if pi.get("project") != first_project:
                different_project = True
            
            if pi.get("custom_site") != first_site:
                different_site = True
        
        error_parts = []
        if different_customer:
            error_parts.append("customers")
        if different_project:
            error_parts.append("projects")
        if different_site:
            error_parts.append("sites")
        
        if error_parts:
            error_message = _("Cannot fetch invoices for different {0}").format(" or ".join(error_parts))
            frappe.throw(error_message)
    
    return True


def get_remaining_qty_to_bill(pi_item):
    return flt(pi_item.custom_pending_si_quantity)


@frappe.whitelist()
def check_purchase_invoice_has_pending_qty(purchase_invoice):
    pi_doc = frappe.get_doc("Purchase Invoice", purchase_invoice)
    
    for item in pi_doc.items:
        if flt(item.custom_pending_si_quantity) > 0:
            return True
    
    return False


@frappe.whitelist()
def make_purchase_receipt(source_name, target_doc=None, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.received_qty = flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (
			(flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate) * flt(source_parent.conversion_rate)
		)
		
		if target.get("custom_refundable"):
			target.margin_type = None
			target.margin_rate_or_amount = 0
			target.rate_with_margin = 0

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True
		return child_filter

	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {
				"doctype": "Purchase Receipt",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Invoice Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_invoice_item",
					"parent": "purchase_invoice",
					"bom": "bom",
					"purchase_order": "purchase_order",
					"po_detail": "purchase_order_item",
					"material_request": "material_request",
					"material_request_item": "material_request_item",
					"wip_composite_asset": "wip_composite_asset",
                    "custom_refundable": "custom_refundable",
					"margin_type": "margin_type",
					"margin_rate_or_amount": "margin_rate_or_amount",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty) and select_item(doc),
			},
			"Purchase Taxes and Charges": {"doctype": "Purchase Taxes and Charges"},
		},
		target_doc,
	)

	return doc
