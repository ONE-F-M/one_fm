import frappe
from frappe import _

from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
from frappe.utils import nowdate



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
    
    def on_update_after_submit(self):
        self.update_purchased_quantities()

    def on_cancel(self):
        self.update_purchased_quantities()

    def update_purchased_quantities(self):
        if not self.one_fm_request_for_purchase:
            return
    
        # Fetch all purchase orders linked to the same Request for Purchase
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

            # Sum purchased quantities from all purchase orders
            item_qty = frappe.db.get_all(
                "Purchase Order Item", 
                {"parent": ["IN", purchase_orders], "item_code": obj.item_code, 'parentfield': 'items'},
                pluck="qty"
            )
            new_qty = sum(item_qty) if item_qty else 0
            
            
            # Update purchased quantity in Request for Purchase Item
            update_purchased_qty(new_qty, self.one_fm_request_for_purchase, obj.item_code, "Request for Purchase Item", "purchased_quantity")


            # If Request for Material exists, update the corresponding quantity
            if request_for_material:
                update_purchased_qty(new_qty, request_for_material, obj.item_code, "Request for Material Item", "purchased_qty")


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

                