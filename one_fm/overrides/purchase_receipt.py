import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
import json

from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt



def get_rfm_in_purchase_receipt(doc):
    po = None
    for each in doc.items:
        if each.purchase_order:
            po = each.purchase_order
            break
    if po:
        po_doc = frappe.get_doc("Purchase Order", po)
        if po_doc.request_for_material:
            return po_doc.request_for_material
        elif po_doc.one_fm_request_for_purchase:
            rfp_doc = frappe.get_doc("Request for Purchase", po_doc.one_fm_request_for_purchase)
            return rfp_doc.request_for_material
            
    
    
def update_received_qty(doc, method):
    """Update received_qty on each item row of the linked Request for Material.

    Rules:
    - Link via parent field: custom_request_for_material on Purchase Receipt.
    - Aggregate across all submitted (docstatus=1) Purchase Receipts for that RFM.
    - Include returns: subtract qty for PRs where is_return=1.
    - Sum per item_code; for each RFM item row with that item_code set received_qty to the total (full amount on every matching row).
    - Skip silently if no link or RFM missing.
    - Re-run on submit, cancel, and update_after_submit (hook should call this).
    - Use frappe.log_error for unexpected errors; otherwise silent.
    """
    rfm_name = getattr(doc, 'custom_request_for_material', None)
    if not rfm_name:
        rfm_name = get_rfm_in_purchase_receipt(doc)
        
    if not frappe.db.exists('Request for Material', rfm_name):
        
        return  # silent skip

    try:
        # Aggregate quantities from all submitted Purchase Receipts for this RFM
        # Negative for returns.
        pr_items = frappe.db.sql(
            """
            SELECT pri.item_code,
                   SUM(pri.qty) AS total_received
            FROM `tabPurchase Receipt Item` pri
            INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            WHERE pr.docstatus = 1
              AND pr.custom_request_for_material = %(rfm_name)s
            GROUP BY pri.item_code
            """,
            {"rfm_name": rfm_name},
            as_dict=True,
        )
        totals = {row.item_code: row.total_received for row in pr_items if row.item_code}
       
        # Fetch RFM item rows
        rfm_items = frappe.db.sql(
            """
            SELECT name, item_code
            FROM `tabRequest for Material Item`
            WHERE parent = %(parent)s
            """,
            {"parent": rfm_name},
            as_dict=True,
        )

        # Update each RFM item row (full aggregate on each matching row). Default 0 if not found.
        for r in rfm_items:
            item_code = r.item_code
            
            if not item_code:
                continue  # row without item_code (business rule might prevent this)
            received = totals.get(item_code, 0) or 0
            frappe.db.set_value('Request for Material Item', r.name, 'received_qty', received, update_modified=False)

    except Exception as e:
        frappe.log_error(title='update_received_qty failed', message=f'RFM: {rfm_name} PR: {getattr(doc, "name", "?")} Error: {e}')


def validate_serial_batch_no(row):
    """
        Validate that the batch in the serial and batch bundle doctype has the relevant data for the supplier
    """
    if row.serial_and_batch_bundle:
        serial_batch_bundle_doc  = frappe.get_doc("Serial and Batch Bundle",row.serial_and_batch_bundle)
        if serial_batch_bundle_doc.has_batch_no:
            for each in serial_batch_bundle_doc.entries:
                batch_details = frappe.get_all("Batch",{'name':each.batch_no},['manufacturing_date','expiry_date','supplier_batch_id'])
                if batch_details:
                    row.manufacturing_date = batch_details[0].get('manufacturing_date')
                    row.expiry_date = batch_details[0].get('expiry_date')
                    row.supplier_batch_id = batch_details[0].get('supplier_batch_id')


def validate_item_batch(doc, method):
    for item in doc.items:
        item_det = frappe.db.sql(
            """select name, item_name, has_batch_no, docstatus, has_expiry_date,
            is_stock_item, has_variants, stock_uom, create_new_batch
            from tabItem where name=%s""",
            item.item_code,
            as_dict=True,
        )
        if item_det and len(item_det) > 0 and item_det[0].has_batch_no == 1:
            batch_item = (
                item.item_code
                if item.item_code == item_det[0].item_name
                else item.item_code + ":" + item_det[0].item_name
            )
            error_msg = False
            validate_serial_batch_no(item)
            if not item.supplier_batch_id:
                error_msg = "Supplier batch number"
            if item_det[0].has_expiry_date and not item.manufacturing_date and not item.expiry_date:
                if error_msg:
                    error_msg += " and Manufacturing/Expiry date"
                else:
                    error_msg = "Manufacturing/Expiry date"
            if error_msg:
                frappe.throw(_(error_msg + " - mandatory for Item {0}").format(batch_item))


@frappe.whitelist()
def make_purchase_receipt_invoice(source_name, target_doc=None, args=None):
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


class PurchaseReceiptOverride(PurchaseReceipt):
    def on_submit(self):
        super(PurchaseReceiptOverride, self).on_submit()
        self.update_refundable_assets()


    def update_refundable_assets(self):
        for item in self.items:
            if not item.get('custom_refundable'):
                continue

            item_master = frappe.db.get_value(
                'Item', 
                item.item_code, 
                ['is_fixed_asset', 'auto_create_assets'], 
                as_dict=True
            )
            
            if not item_master.is_fixed_asset:
                continue
            
            if not item_master.auto_create_assets:
                continue
            
            asset_name = frappe.db.get_value(
                'Asset',
                {
                    'purchase_receipt': self.name,
                    'purchase_receipt_item': item.name,
                    'item_code': item.item_code
                }
            )
            
            if asset_name:
                self.update_asset_for_refundable(asset_name, item)
                frappe.msgprint(
                    _("Updated asset {0} for refundable item {1}").format(asset_name, item.item_code),
                    alert=True
                )
    
    
    def update_asset_for_refundable(self, asset_name, item):
        asset = frappe.get_doc('Asset', asset_name)
        
        asset.custom_is_refundable = 1
        asset.asset_owner = 'Customer'
        asset.customer = self.custom_customer if self.custom_customer else None
        
        if not asset.available_for_use_date:
            asset.available_for_use_date = self.posting_date
        
        asset.flags.ignore_validate_update_after_submit = True
        asset.save(ignore_permissions=True)
        
        return asset.name