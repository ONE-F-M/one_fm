def get_purchase_invoice_properties():
    return [
        {
            "property": "default",
            "property_type": "Text",
            "value": "PIN-.YYYY.-.######",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "field_order",
            "property_type": "Data",
            "value": '["title", "naming_series", "supplier", "supplier_name", "tax_id", "company", "column_break_6", "posting_date", "posting_time", "set_posting_time", "employee_advance", "due_date", "column_break1", "is_paid", "is_return", "is_subcontracted", "return_against", "update_outstanding_for_self", "update_billed_amount_in_purchase_order", "update_billed_amount_in_purchase_receipt", "apply_tds", "tax_withholding_category", "amended_from", "supplier_invoice_details", "bill_no", "column_break_15", "bill_date", "accounting_dimensions_section", "cost_center", "dimension_col_break", "custom_customer", "project", "custom_site", "custom_refundable", "custom_margin_type", "custom_margin_rate_or_amount", "currency_and_price_list", "currency", "conversion_rate", "use_transaction_date_exchange_rate", "column_break2", "buying_price_list", "price_list_currency", "plc_conversion_rate", "ignore_pricing_rule", "sec_warehouse", "scan_barcode", "last_scanned_warehouse", "col_break_warehouse", "update_stock", "set_warehouse", "set_from_warehouse", "rejected_warehouse", "supplier_warehouse", "items_section", "items", "section_break_26", "total_qty", "total_net_weight", "column_break_50", "base_total", "base_net_total", "column_break_28", "total", "net_total", "tax_withholding_net_total", "base_tax_withholding_net_total", "taxes_section", "tax_category", "taxes_and_charges", "column_break_58", "shipping_rule", "column_break_49", "incoterm", "named_place", "section_break_51", "taxes", "totals", "base_taxes_and_charges_added", "base_taxes_and_charges_deducted", "base_total_taxes_and_charges", "column_break_40", "taxes_and_charges_added", "taxes_and_charges_deducted", "total_taxes_and_charges", "section_break_49", "base_grand_total", "base_rounding_adjustment", "base_rounded_total", "base_in_words", "column_break8", "grand_total", "rounding_adjustment", "use_company_roundoff_cost_center", "rounded_total", "in_words", "total_advance", "outstanding_amount", "disable_rounded_total", "section_break_44", "apply_discount_on", "base_discount_amount", "column_break_46", "additional_discount_percentage", "discount_amount", "tax_withheld_vouchers_section", "tax_withheld_vouchers", "sec_tax_breakup", "other_charges_calculation", "pricing_rule_details", "pricing_rules", "raw_materials_supplied", "supplied_items", "payments_tab", "payments_section", "mode_of_payment", "base_paid_amount", "clearance_date", "col_br_payments", "cash_bank_account", "paid_amount", "advances_section", "allocate_advances_automatically", "only_include_allocated_payments", "get_advances", "advances", "advance_tax", "write_off", "write_off_amount", "base_write_off_amount", "column_break_61", "write_off_account", "write_off_cost_center", "address_and_contact_tab", "section_addresses", "supplier_address", "address_display", "col_break_address", "contact_person", "contact_display", "contact_mobile", "contact_email", "company_shipping_address_section", "dispatch_address", "dispatch_address_display", "column_break_126", "shipping_address", "shipping_address_display", "company_billing_address_section", "billing_address", "column_break_130", "billing_address_display", "terms_tab", "payment_schedule_section", "payment_terms_template", "ignore_default_payment_terms_template", "payment_schedule", "terms_section_break", "tc_name", "terms", "more_info_tab", "status_section", "status", "column_break_177", "per_received", "accounting_details_section", "credit_to", "party_account_currency", "is_opening", "against_expense_account", "column_break_63", "unrealized_profit_loss_account", "subscription_section", "subscription", "auto_repeat", "update_auto_repeat_reference", "column_break_114", "from_date", "to_date", "printing_settings", "letter_head", "group_same_items", "column_break_112", "select_print_heading", "language", "sb_14", "on_hold", "release_date", "cb_17", "hold_comment", "additional_info_section", "is_internal_supplier", "represents_company", "supplier_group", "column_break_147", "inter_company_invoice_reference", "is_old_subcontracting_flow", "remarks", "custom_sales_invoice", "connections_tab"]',
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocType"
        },
        {
            "property": "options",
            "property_type": "Text",
            "value": "ACC-PINV-.YYYY.-\nPIN-.YYYY.-.######",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "scan_barcode"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "cost_center"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "payment_schedule"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "due_date"
        }
    ]
