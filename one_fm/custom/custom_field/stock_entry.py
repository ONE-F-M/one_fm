def get_stock_entry_custom_fields():
    return {
        "Stock Entry": [
            {
                "label": "Site Supervisor Name",
                "fieldname": "custom_site_supervisor_name",
                "insert_after": "custom_site_supervisor",
                "fieldtype": "Data",
                "read_only": 1,
            },
            {
                "fieldname": "one_fm_request_for_material",
                "fieldtype": "Link",
                "label": "Request for Material",
                "insert_after": "stock_entry_type",
                "options": "Request for Material",
                "read_only": 1
            },
            {
                "fieldname": "sb_attachments",
                "fieldtype": "Section Break",
                "label": "SB Attachments",
                "insert_after": "value_difference"
            },
            {
                "fieldname": "delivery_note_attachment",
                "fieldtype": "Attach",
                "label": "Delivery Note Attachment",
                "insert_after": "sb_attachments"
            },
            {
                "fieldname": "inspection_form_attachment",
                "fieldtype": "Attach",
                "label": "Inspection Form Attachment",
                "insert_after": "delivery_note_attachment"
            },
            {
                "fieldname": "linked_employee_uniform",
                "fieldtype": "Link",
                "label": "Linked Employee Uniform",
                "insert_after": "posting_time",
                "options": "Employee Uniform",
                "read_only": 1
            },
            {
                "fieldname": "linked_request_for_material",
                "fieldtype": "Link",
                "label": "Linked Request for Material",
                "insert_after": "linked_employee_uniform",
                "options": "Request for Material",
                "read_only": 1
            },
        ]
    }
