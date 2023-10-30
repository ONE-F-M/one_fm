import frappe
from frappe import _

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
            if not item.supplier_batch_id:
                error_msg = "Supplier batch number"
            if item_det[0].has_expiry_date and not item.manufacturing_date and not item.expiry_date:
                if error_msg:
                    error_msg += " and Manufacturing/Expiry date"
                else:
                    error_msg = "Manufacturing/Expiry date"
            if error_msg:
                frappe.throw(_(error_msg + " - mandatory for Item {0}").format(batch_item))
