from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class SalesInvoiceOverride(SalesInvoice):

    def validate(self):
        super(SalesInvoiceOverride, self).validate()
        self.update_purchase_invoice_link()

    def on_submit(self):
        super(SalesInvoiceOverride, self).on_submit()
        self.update_purchase_invoice_pending_quantities("submit")
        self.update_purchase_invoice_link()

    def on_cancel(self):
        super(SalesInvoiceOverride, self).on_cancel()
        self.update_purchase_invoice_pending_quantities("cancel")
        self.clear_purchase_invoice_link()

    def update_purchase_invoice_pending_quantities(self, action):
        for item in self.items:
            if item.get("custom_purchase_invoice") and item.get("custom_purchase_invoice_item"):
                pi_item = frappe.get_doc("Purchase Invoice Item", item.custom_purchase_invoice_item)
                
                current_pending = flt(pi_item.custom_pending_si_quantity)
                item_qty = flt(item.qty)
                
                if action == "submit":
                    new_pending = current_pending - item_qty
                elif action == "cancel":
                    new_pending = current_pending + item_qty
                else:
                    new_pending = current_pending
                
                new_pending = max(new_pending, 0)
                
                frappe.db.set_value(
                    "Purchase Invoice Item",
                    item.custom_purchase_invoice_item,
                    "custom_pending_si_quantity",
                    new_pending,
                    update_modified=False
                )

    def before_save(self):
        super(SalesInvoiceOverride, self).before_save()
        self.populate_contract_item_categorywise_summary()


    def populate_contract_item_categorywise_summary(self):
        category_amounts = defaultdict(float)
        
        for item in self.items:
            category = item.get("custom_contract_item_category")
            if category:
                category_amounts[category] += item.get("amount", 0)
        
        # Build the new summary as a list of dicts, sorted by category for consistency
        new_summary = [
            {
                "contract_item_category": category,
                "base_net_amount": amount
            }
            for category, amount in sorted(category_amounts.items())
        ]

        # Normalize current summary for comparison (ignore order)
        current_summary = [
            {
                "contract_item_category": row.contract_item_category,
                "base_net_amount": row.base_net_amount
            }
            for row in self.get("custom_contract_item_categorywise_summary", [])
        ]
        # Sort both lists for reliable comparison
        new_summary_sorted = sorted(new_summary, key=lambda x: x["contract_item_category"])
        current_summary_sorted = sorted(current_summary, key=lambda x: x["contract_item_category"])

        if new_summary_sorted != current_summary_sorted:
            self.custom_contract_item_categorywise_summary = []
            for entry in new_summary_sorted:
                self.append("custom_contract_item_categorywise_summary", entry)
    def update_purchase_invoice_link(self):
        purchase_invoices = set()
        
        for item in self.items:
            if item.get("custom_purchase_invoice"):
                purchase_invoices.add(item.custom_purchase_invoice)
        
        for pi_name in purchase_invoices:
            frappe.db.set_value(
                "Purchase Invoice",
                pi_name,
                "custom_sales_invoice",
                self.name,
                update_modified=False
            )
            
            frappe.db.commit()

    def clear_purchase_invoice_link(self):
        purchase_invoices = set()
        
        for item in self.items:
            if item.get("custom_purchase_invoice"):
                purchase_invoices.add(item.custom_purchase_invoice)
        
        for pi_name in purchase_invoices:
            linked_si = frappe.db.get_value("Purchase Invoice", pi_name, "custom_sales_invoice")
            
            if linked_si == self.name:
                other_sis = frappe.db.sql("""
                    SELECT DISTINCT si.name
                    FROM `tabSales Invoice` si
                    INNER JOIN `tabSales Invoice Item` si_item ON si_item.parent = si.name
                    WHERE si.docstatus = 1
                    AND si.name != %s
                    AND si_item.custom_purchase_invoice = %s
                    ORDER BY si.posting_date DESC
                    LIMIT 1
                """, (self.name, pi_name), as_dict=1)
                
                new_link = other_sis[0].name if other_sis else None
                
                frappe.db.set_value(
                    "Purchase Invoice",
                    pi_name,
                    "custom_sales_invoice",
                    new_link,
                    update_modified=False
                )
                
                frappe.db.commit()
