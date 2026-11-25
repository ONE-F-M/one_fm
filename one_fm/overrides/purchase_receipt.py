import frappe
from frappe import _


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
                frappe.db.commit()


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
