def get_stock_entry_detail_custom_fields():
    return {
        "Stock Entry Detail": [
            {
                "fieldname": "one_fm_request_for_material",
                "fieldtype": "Link",
                "label": "Request for Material",
                "insert_after": "material_request",
                "options": "Request for Material",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_request_for_material_item",
                "fieldtype": "Link",
                "label": "Request for Material Item",
                "insert_after": "material_request_item",
                "options": "Request for Material Item",
                "read_only": 1
            },
            {
                "fieldname": "linked_employee_uniform_item",
                "fieldtype": "Link",
                "label": "Linked Employee Uniform Item",
                "insert_after": "job_card_item",
                "options": "Employee Uniform Item",
                "read_only": 1
            },
            {
                "fieldname": "linked_rfm_reference",
                "fieldtype": "Link",
                "label": "Linked RFM Reference",
                "insert_after": "linked_employee_uniform_item",
                "options": "Request for Material Item",
                "read_only": 1
            },

        ]
    }