def get_purchase_order_properties():
    return [
        {
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"workflow_state\", \"supplier_section\", \"title\", \"naming_series\", \"supplier\", \"one_fm_request_for_purchase\", \"request_for_material\", \"quotation\", \"supplier_quotation_attachment\", \"quoted_delivery_date\", \"supplier_name\", \"order_confirmation_no\", \"order_confirmation_date\", \"get_items_from_open_material_requests\", \"column_break_7\", \"transaction_date\", \"schedule_date\", \"custom_purchase_order_approver\", \"custom_purchase_order_approver_name\", \"column_break1\", \"company\", \"item_request\", \"apply_tds\", \"tax_withholding_category\", \"is_subcontracted\", \"supplier_warehouse\", \"amended_from\", \"one_fm_po_document_section\", \"one_fm_type_of_purchase\", \"one_fm_certificate_of_origin_required\", \"one_fm_other_documents_required\", \"one_fm_po_document_cb\", \"one_fm_details_of_other_documents\", \"accounting_dimensions_section\", \"cost_center\", \"dimension_col_break\", \"purchase_type\", \"department_manager\", \"project\", \"currency_and_price_list\", \"currency\", \"conversion_rate\", \"cb_price_list\", \"buying_price_list\", \"price_list_currency\", \"plc_conversion_rate\", \"ignore_pricing_rule\", \"before_items_section\", \"scan_barcode\", \"set_from_warehouse\", \"items_col_break\", \"set_warehouse\", \"one_fm_warehouse_location\", \"one_fm_warehouse_contact_person\", \"one_fm_contact_person_phone\", \"one_fm_contact_person_email\", \"items_section\", \"items\", \"sb_last_purchase\", \"total_qty\", \"total_net_weight\", \"column_break_40\", \"base_total\", \"base_net_total\", \"column_break_26\", \"total\", \"net_total\", \"tax_withholding_net_total\", \"base_tax_withholding_net_total\", \"section_break_48\", \"pricing_rules\", \"raw_material_details\", \"set_reserve_warehouse\", \"supplied_items\", \"taxes_section\", \"tax_category\", \"taxes_and_charges\", \"column_break_53\", \"shipping_rule\", \"column_break_50\", \"incoterm\", \"named_place\", \"section_break_52\", \"taxes\", \"totals\", \"base_taxes_and_charges_added\", \"base_taxes_and_charges_deducted\", \"base_total_taxes_and_charges\", \"column_break_39\", \"taxes_and_charges_added\", \"taxes_and_charges_deducted\", \"total_taxes_and_charges\", \"totals_section\", \"base_grand_total\", \"base_rounding_adjustment\", \"base_in_words\", \"base_rounded_total\", \"column_break4\", \"grand_total\", \"rounding_adjustment\", \"rounded_total\", \"disable_rounded_total\", \"in_words\", \"advance_paid\", \"discount_section\", \"apply_discount_on\", \"base_discount_amount\", \"column_break_45\", \"additional_discount_percentage\", \"discount_amount\", \"sec_tax_breakup\", \"other_charges_calculation\", \"address_and_contact_tab\", \"section_addresses\", \"supplier_address\", \"address_display\", \"col_break_address\", \"contact_person\", \"contact_display\", \"contact_mobile\", \"contact_email\", \"shipping_address_section\", \"shipping_address\", \"custom_place_of_delivery\", \"column_break_99\", \"shipping_address_display\", \"company_billing_address_section\", \"billing_address\", \"column_break_103\", \"billing_address_display\", \"drop_ship\", \"customer\", \"customer_name\", \"column_break_19\", \"customer_contact_person\", \"customer_contact_display\", \"customer_contact_mobile\", \"customer_contact_email\", \"terms_tab\", \"payment_schedule_section\", \"payment_terms_template\", \"payment_schedule\", \"signatures\", \"authority_signature\", \"terms_section_break\", \"tc_name\", \"terms\", \"other_conditions\", \"custom_terms_of_shipment\", \"more_info_tab\", \"tracking_section\", \"status\", \"column_break_75\", \"per_billed\", \"per_received\", \"column_break5\", \"letter_head\", \"group_same_items\", \"column_break_86\", \"select_print_heading\", \"language\", \"subscription_section\", \"from_date\", \"to_date\", \"column_break_97\", \"auto_repeat\", \"update_auto_repeat_reference\", \"additional_info_section\", \"is_internal_supplier\", \"represents_company\", \"ref_sq\", \"custom_rfq_number\", \"custom_purchase_manager_approval_date\", \"custom_purchase_officer_approval_date\", \"packaging_type\", \"column_break_74\", \"party_account_currency\", \"inter_company_order_reference\", \"is_old_subcontracting_flow\", \"connections_tab\"]",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocType"
        },
        {
            "property": "default_print_format",
            "property_type": "Data",
            "value": "Purchase Order",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocType"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "due_date"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "payment_schedule"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "scan_barcode"
        },
        {
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "is_subcontracted"
        },
        {
            "property": "options",
            "property_type": "Text",
            "value": "PUR-ORD-.YYYY.-\nPOR-.YYYY.-.######",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "default",
            "property_type": "Text",
            "value": "POR-.YYYY.-.######",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "default",
            "property_type": "Text",
            "value": "1",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "disable_rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Order",
            "doctype_or_field": "DocField",
            "field_name": "disable_rounded_total"
        }
    ]
