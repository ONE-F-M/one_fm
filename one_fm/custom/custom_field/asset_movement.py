def get_asset_movement_custom_fields():
    return {
        "Asset Movement": [
            {
                "fieldname": "delivery_receipt",
                "fieldtype": "Attach",
                "insert_after": "assets",
                "label": "Delivery Receipt"
            },
            {
                "fieldname": "rfm_reference",
                "fieldtype": "Link",
                "label": "Request for Material",
                "options": "Request for Material",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            },
            {
                # Auto-populated on save from the To Employee's linked User ID.
                # Used by the "Asset Movement - Employee" assignment rule to route
                # the acceptance task to the incoming employee.
                "fieldname": "custom_handover_employee_user",
                "fieldtype": "Link",
                "label": "Handover Employee User",
                "options": "User",
                "insert_after": "reference_doctype",
                "hidden": 1,
                "read_only": 1,
                "no_copy": 1,
                "print_hide": 1,
            },
            {
                # Required only when the incoming employee rejects the handover.
                "fieldname": "custom_reason_for_rejection",
                "fieldtype": "Small Text",
                "label": "Reason for Rejection",
                "insert_after": "delivery_receipt",
                "no_copy": 1,
            }
        ]
    }
