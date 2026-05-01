from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class SalesInvoiceOverride(SalesInvoice):

    def validate(self):
        super(SalesInvoiceOverride, self).validate()
        self.update_purchase_invoice_link()
        if self.custom_refundable:
            self.validate_contract_item_categories()
        self.validate_contract_item_rates()

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
        # `self.get("custom_contract_item_categorywise_summary")` can be None on new docs,
        # so coerce to an empty list before iterating to avoid `'NoneType' object is not iterable`.
        existing_rows = self.get("custom_contract_item_categorywise_summary") or []
        current_summary = [
            {
                "contract_item_category": row.contract_item_category,
                "base_net_amount": row.base_net_amount
            }
            for row in existing_rows
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
    
    def validate_contract_item_categories(self):
        for item in self.items:
            if not item.custom_contract_item_category:
                frappe.throw(
                    _("Row #{0}: Contract Item Category is mandatory for Refundable Sales Invoices")
                    .format(item.idx)
                )
            
            if self.customer and self.project:
                contract = frappe.db.get_value(
                    'Contracts',
                    {'client': self.customer, 'project': self.project},
                    'name'
                )
                
                if contract:
                    valid_category = frappe.db.exists(
                        'Contract Item',
                        {
                            'parent': contract,
                            'item_type': 'Items',
                            'contract_item_category': item.custom_contract_item_category
                        }
                    )
                    
                    if not valid_category:
                        frappe.throw(
                            _("Row #{0}: '{1}' is not a valid category for this Contract")
                            .format(item.idx, item.custom_contract_item_category)
                        )

    def validate_contract_item_rates(self):
        """Story 3: Prevent manual rate adjustments on Sales Invoices generated from Contracts"""
        for item in self.items:
            if item.get("custom_contract") and item.get("custom_contract_item"):
                contract_rate = frappe.db.get_value("Contract Item", item.custom_contract_item, "rate")
                
                # Check if it's an Item (instead of Service) which might use amount/rate depending on is_fixed_fee
                if contract_rate is None:
                    # Could be a non-service item, fetch full row to check
                    contract_item = frappe.db.get_value("Contract Item", item.custom_contract_item, ["rate", "amount", "is_fixed_fee"], as_dict=True)
                    if contract_item:
                        contract_rate = flt(contract_item.amount) if contract_item.is_fixed_fee else flt(contract_item.rate)
                
                if contract_rate is not None and flt(item.rate) != flt(contract_rate):
                    frappe.throw(
                        _("Row #{0}: The Rate for Item '{1}' ({2}) does not match the Contract Rate ({3}). Manual rate adjustment is not permitted for Contract items.")
                        .format(item.idx, item.item_code, flt(item.rate), flt(contract_rate))
                    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_filtered_contract_item_categories(doctype, txt, searchfield, start, page_len, filters):

    customer = filters.get('customer')
    project = filters.get('project')
    
    if not customer or not project:
        return []
    

    contract = frappe.db.get_value(
        'Contracts',
        {
            'client': customer,
            'project': project
        },
        'name'
    )
    
    if not contract:
        frappe.msgprint(_("No contract found for Customer: {0} and Project: {1}").format(customer, project))
        return []
    
    categories = frappe.db.sql("""
        SELECT DISTINCT ci.contract_item_category
        FROM `tabContract Item` ci
        WHERE ci.parent = %(contract)s
        AND ci.item_type = 'Items'
        AND ci.contract_item_category IS NOT NULL
        AND ci.contract_item_category != ''
        AND ci.contract_item_category LIKE %(txt)s
        ORDER BY ci.contract_item_category
        LIMIT %(page_len)s OFFSET %(start)s
    """, {
        'contract': contract,
        'txt': '%{}%'.format(txt),
        'start': start,
        'page_len': page_len
    }, as_dict=False)
    
    return categories