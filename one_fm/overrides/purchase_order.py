import frappe
import json
from frappe import _
from frappe.utils import cint, cstr, flt, get_link_to_form
from frappe.model.mapper import get_mapped_doc
from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
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
		target.qty = flt(obj.qty) if is_unit_price_row(obj) else flt(obj.qty) - flt(obj.received_qty)
		target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
		target.base_amount = (
			(flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate) * flt(source_parent.conversion_rate)
		)

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
				"field_map": {"supplier_warehouse": "supplier_warehouse"},
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

                