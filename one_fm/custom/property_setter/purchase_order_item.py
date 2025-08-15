def get_purchase_order_item_properties():
    return [
        {
            "property": "in_list_view",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order Item",
            "doctype_or_field": "DocField",
            "field_name": "warehouse"
        },
        {
            "property": "in_list_view",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Order Item",
            "doctype_or_field": "DocField",
            "field_name": "schedule_date"
        },
        {
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"fg_item\", \"fg_item_qty\", \"item_code\", \"is_customer_asset\", \"supplier_part_no\", \"item_name\", \"brand\", \"product_bundle\", \"column_break_4\", \"schedule_date\", \"expected_delivery_date\", \"item_group\", \"section_break_5\", \"description\", \"col_break1\", \"image\", \"image_view\", \"quantity_and_rate\", \"qty\", \"stock_uom\", \"col_break2\", \"uom\", \"conversion_factor\", \"stock_qty\", \"sec_break1\", \"price_list_rate\", \"last_purchase_rate\", \"col_break3\", \"base_price_list_rate\", \"discount_and_margin_section\", \"margin_type\", \"margin_rate_or_amount\", \"rate_with_margin\", \"column_break_28\", \"discount_percentage\", \"discount_amount\", \"base_rate_with_margin\", \"sec_break2\", \"rate\", \"amount\", \"item_tax_template\", \"col_break4\", \"base_rate\", \"base_amount\", \"pricing_rules\", \"stock_uom_rate\", \"is_free_item\", \"apply_tds\", \"section_break_29\", \"net_rate\", \"net_amount\", \"column_break_32\", \"base_net_rate\", \"base_net_amount\", \"warehouse_and_reference\", \"from_warehouse\", \"warehouse\", \"column_break_54\", \"actual_qty\", \"company_total_stock\", \"references_section\", \"material_request\", \"request_for_material\", \"material_request_item\", \"request_for_material_item\", \"sales_order\", \"sales_order_item\", \"sales_order_packed_item\", \"supplier_quotation\", \"supplier_quotation_item\", \"col_break5\", \"delivered_by_supplier\", \"against_blanket_order\", \"blanket_order\", \"blanket_order_rate\", \"section_break_56\", \"received_qty\", \"returned_qty\", \"column_break_60\", \"billed_amt\", \"accounting_details\", \"expense_account\", \"column_break_fyqr\", \"wip_composite_asset\", \"manufacture_details\", \"manufacturer\", \"manufacturer_part_no\", \"column_break_14\", \"bom\", \"include_exploded_items\", \"item_weight_details\", \"weight_per_unit\", \"total_weight\", \"column_break_40\", \"weight_uom\", \"accounting_dimensions_section\", \"project\", \"dimension_col_break\", \"cost_center\", \"more_info_section_break\", \"is_fixed_asset\", \"item_tax_rate\", \"section_break_72\", \"production_plan\", \"production_plan_item\", \"production_plan_sub_assembly_item\", \"page_break\"]",
            "doc_type": "Purchase Order Item",
            "doctype_or_field": "DocType"
        }
    ]
