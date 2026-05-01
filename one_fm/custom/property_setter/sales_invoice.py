def get_sales_invoice_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": '["workflow_state", "customer_section", "title", "naming_series", "customer", "loan", "customer_name", "contracts", "balance_in_advance_account", "settlement_amount", "tax_id", "company", "company_tax_id", "column_break1", "posting_date", "posting_time", "set_posting_time", "due_date", "column_break_14", "is_pos", "pos_profile", "is_consolidated", "is_return", "return_against", "update_outstanding_for_self", "update_billed_amount_in_sales_order", "automatic_settlement", "update_billed_amount_in_delivery_note", "is_debit_note", "amended_from", "accounting_dimensions_section", "cost_center", "dimension_col_break", "project", "currency_and_price_list", "currency", "conversion_rate", "column_break2", "selling_price_list", "price_list_currency", "plc_conversion_rate", "ignore_pricing_rule", "section_break_53", "social_security_item", "social_security_items", "add_social_security", "items_section", "scan_barcode", "add_timesheet_amount", "update_stock", "column_break_39", "set_warehouse", "set_target_warehouse", "section_break_42", "items", "section_break_30", "total_qty", "total_net_weight", "column_break_32", "base_total", "base_net_total", "column_break_52", "total", "net_total", "taxes_section", "tax_category", "taxes_and_charges", "column_break_38", "shipping_rule", "column_break_55", "incoterm", "named_place", "section_break_40", "taxes", "section_break_43", "base_total_taxes_and_charges", "column_break_47", "total_taxes_and_charges", "totals", "base_grand_total", "base_rounding_adjustment", "base_rounded_total", "base_in_words", "column_break5", "grand_total", "rounding_adjustment", "use_company_roundoff_cost_center", "rounded_total", "in_words", "total_advance", "outstanding_amount", "disable_rounded_total", "section_break_49", "apply_discount_on", "base_discount_amount", "is_cash_or_non_trade_discount", "additional_discount_account", "column_break_51", "additional_discount_percentage", "discount_amount", "sec_tax_breakup", "other_charges_calculation", "pricing_rule_details", "pricing_rules", "packing_list", "packed_items", "product_bundle_help", "time_sheet_list", "timesheets", "section_break_104", "total_billing_hours", "column_break_106", "total_billing_amount", "payments_tab", "payments_section", "cash_bank_account", "payments", "section_break_84", "base_paid_amount", "column_break_86", "paid_amount", "section_break_88", "base_change_amount", "column_break_90", "change_amount", "account_for_change_amount", "advances_section", "allocate_advances_automatically", "only_include_allocated_payments", "get_advances", "advances", "write_off_section", "write_off_amount", "base_write_off_amount", "write_off_outstanding_amount_automatically", "column_break_74", "write_off_account", "write_off_cost_center", "loyalty_points_redemption", "redeem_loyalty_points", "loyalty_points", "loyalty_amount", "column_break_77", "loyalty_program", "loyalty_redemption_account", "loyalty_redemption_cost_center", "contact_and_address_tab", "address_and_contact", "customer_address", "address_display", "col_break4", "contact_person", "contact_display", "contact_mobile", "contact_email", "territory", "shipping_address_section", "shipping_address_name", "shipping_address", "shipping_addr_col_break", "dispatch_address_name", "dispatch_address", "company_address_section", "company_address", "company_addr_col_break", "company_address_display", "terms_tab", "payment_schedule_section", "ignore_default_payment_terms_template", "payment_terms_template", "payment_schedule", "terms_section_break", "tc_name", "terms", "custom_client_confirmation_copy", "more_info_tab", "customer_po_details", "po_no", "column_break_23", "po_date", "po", "more_info", "debit_to", "party_account_currency", "is_opening", "column_break8", "unrealized_profit_loss_account", "against_income_account", "sales_team_section_break", "sales_partner", "amount_eligible_for_commission", "column_break10", "commission_rate", "total_commission", "section_break2", "sales_team", "edit_printing_settings", "letter_head", "group_same_items", "column_break_84", "select_print_heading", "language", "format", "subscription_section", "subscription", "from_date", "auto_repeat", "column_break_140", "to_date", "update_auto_repeat_reference", "more_information", "status", "inter_company_invoice_reference", "campaign", "represents_company", "source", "customer_group", "col_break23", "is_internal_customer", "is_discounted", "remarks", "repost_required", "connections_tab"]'
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "scan_barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "due_date",
            "property": "print_hide",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "payment_schedule",
            "property": "print_hide",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "cost_center",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total",
            "property": "hidden",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total",
            "property": "print_hide",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total",
            "property": "hidden",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total",
            "property": "print_hide",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "in_words",
            "property": "hidden",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "in_words",
            "property": "print_hide",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "options",
            "property_type": "Text",
            "value": "ACC-SINV-.YYYY.-"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "tax_id",
            "property": "hidden",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "tax_id",
            "property": "print_hide",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "project",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "contracts.project"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "project",
            "property": "fetch_if_empty",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocField",
            "field_name": "taxes_section",
            "property": "collapsible",
            "property_type": "Check",
            "value": "1"
        }
    ]