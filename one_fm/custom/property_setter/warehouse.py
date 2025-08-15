def get_warehouse_properties():
    return [
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Warehouse",
            "doctype_or_field": "DocField",
            "field_name": "disabled"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Warehouse",
            "doctype_or_field": "DocField",
            "field_name": "warehouse_contact_info"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Warehouse",
            "doctype_or_field": "DocField",
            "field_name": "transit_section"
        },
        {
            "property": "collapsible",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Warehouse",
            "doctype_or_field": "DocField",
            "field_name": "column_break_3"
        },
        {
            "property": "label",
            "property_type": "Data",
            "value": "Account and Cost Center",
            "doc_type": "Warehouse",
            "doctype_or_field": "DocField",
            "field_name": "column_break_3"
        },
        {
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"warehouse_detail\", \"disabled\", \"warehouse_name\", \"warehouse_code\", \"one_fm_store_keeper\", \"column_break_c21su\", \"status\", \"column_break_3\", \"is_group\", \"parent_warehouse\", \"cost_center\", \"allow_zero_valuation_rate\", \"column_break_4\", \"account\", \"company\", \"project_and_department_sb\", \"one_fm_is_project_warehouse\", \"one_fm_project\", \"one_fm_site\", \"one_fm_location\", \"column_break_2azq1\", \"is_uniform_warehouse\", \"department\", \"address_and_contact\", \"address_html\", \"column_break_10\", \"contact_html\", \"warehouse_contact_info\", \"email_id\", \"phone_no\", \"mobile_no\", \"column_break0\", \"address_line_1\", \"address_line_2\", \"city\", \"state\", \"pin\", \"transit_section\", \"warehouse_type\", \"column_break_qajx\", \"default_in_transit_warehouse\", \"tree_details\", \"lft\", \"rgt\", \"old_parent\"]",
            "doc_type": "Warehouse",
            "doctype_or_field": "DocType"
        }
    ]
