import frappe

def execute():
    """
    Fix missing one_fm_request_for_purchase field values in Purchase Orders
    that should be linked to Request for Purchase documents.
    
    This addresses the issue where some Purchase Orders don't show up in the
    RFP dashboard connections section.
    """
    
    # Find Purchase Orders that might be missing the one_fm_request_for_purchase field
    # but have a request_for_material that could help us trace back
    
    pos_with_rfm = frappe.db.sql("""
        SELECT 
            po.name as po_name,
            po.request_for_material,
            po.one_fm_request_for_purchase,
            rfp.name as rfp_name
        FROM 
            `tabPurchase Order` po
        LEFT JOIN 
            `tabRequest for Purchase` rfp ON rfp.request_for_material = po.request_for_material
        WHERE 
            po.docstatus = 1
            AND po.request_for_material IS NOT NULL 
            AND po.request_for_material != ''
            AND (po.one_fm_request_for_purchase IS NULL OR po.one_fm_request_for_purchase = '')
            AND rfp.name IS NOT NULL
    """, as_dict=True)
    
    if not pos_with_rfm:
        frappe.log_error("No Purchase Orders found with missing RFP links", "RFP Link Fix")
        return
    
    frappe.log_error(f"Found {len(pos_with_rfm)} Purchase Orders with missing RFP links", "RFP Link Fix")
    
    # Update Purchase Orders with the correct Request for Purchase link
    updated_count = 0
    for po_data in pos_with_rfm:
        try:
            frappe.db.set_value(
                "Purchase Order", 
                po_data.po_name, 
                "one_fm_request_for_purchase", 
                po_data.rfp_name,
                update_modified=False
            )
            updated_count += 1
            frappe.log_error(f"Updated PO {po_data.po_name} with RFP {po_data.rfp_name}", "RFP Link Fix")
        except Exception as e:
            frappe.log_error(f"Failed to update PO {po_data.po_name}: {e}", "RFP Link Fix Error")
    
    # Also try to find Purchase Orders created from RFPs that might have missing links
    # by checking if there are Purchase Order Items that match Request for Purchase Items
    pos_missing_rfp = frappe.db.sql("""
        SELECT DISTINCT
            po.name as po_name,
            rfp.name as rfp_name
        FROM 
            `tabPurchase Order` po
        INNER JOIN 
            `tabPurchase Order Item` poi ON poi.parent = po.name
        INNER JOIN 
            `tabRequest for Purchase Item` rfpi ON rfpi.item_code = poi.item_code
        INNER JOIN 
            `tabRequest for Purchase` rfp ON rfp.name = rfpi.parent
        WHERE 
            po.docstatus = 1
            AND (po.one_fm_request_for_purchase IS NULL OR po.one_fm_request_for_purchase = '')
            AND rfp.docstatus = 1
            AND ABS(DATEDIFF(po.transaction_date, rfp.transaction_date)) <= 30
    """, as_dict=True)
    
    for po_data in pos_missing_rfp:
        try:
            # Double-check this is a valid connection by ensuring some items match
            matching_items = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM 
                    `tabPurchase Order Item` poi
                INNER JOIN 
                    `tabRequest for Purchase Item` rfpi ON rfpi.item_code = poi.item_code
                WHERE 
                    poi.parent = %s AND rfpi.parent = %s
            """, (po_data.po_name, po_data.rfp_name))
            
            if matching_items and matching_items[0][0] > 0:
                frappe.db.set_value(
                    "Purchase Order", 
                    po_data.po_name, 
                    "one_fm_request_for_purchase", 
                    po_data.rfp_name,
                    update_modified=False
                )
                updated_count += 1
                frappe.log_error(f"Updated PO {po_data.po_name} with RFP {po_data.rfp_name} (by item matching)", "RFP Link Fix")
        except Exception as e:
            frappe.log_error(f"Failed to update PO {po_data.po_name} by item matching: {e}", "RFP Link Fix Error")
    
    frappe.db.commit()
    
    frappe.log_error(f"RFP Link Fix completed. Updated {updated_count} Purchase Orders", "RFP Link Fix")
    print(f"Fixed RFP links for {updated_count} Purchase Orders")