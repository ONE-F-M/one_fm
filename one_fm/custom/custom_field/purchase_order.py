def get_purchase_order_custom_fields():
    return {
        "Purchase Order": [
            {
                "fieldname": "custom_packaging_type",
                "label": "Packaging Type",
                "fieldtype": "Data",
                "insert_after": "custom_purchase_officer_approval_date",
                "translatable": 1
            },
            {
                "fieldname": "custom_purchase_manager_approval_date",
                "label": "Purchase Manager Approval Date",
                "fieldtype": "Date",
                "insert_after": "custom_rfq_number",
                "hidden": 1
            },
            {
                "fieldname": "custom_purchase_officer_approval_date",
                "label": "Purchase Officer Approval Date",
                "fieldtype": "Date",
                "insert_after": "custom_purchase_manager_approval_date",
                "hidden": 1
            },
            {
                "fieldname": "custom_rfq_number",
                "label": "RFQ Number",
                "fieldtype": "Data",
                "insert_after": "ref_sq",
                "translatable": 1
            },
            {
                "fieldname": "custom_terms_of_shipment",
                "label": "Terms of Shipment",
                "fieldtype": "Small Text",
                "insert_after": "other_conditions",
                "translatable": 1
            },
            {
                "fieldname": "custom_place_of_delivery",
                "label": "Place of Delivery",
                "fieldtype": "Small Text",
                "insert_after": "shipping_address",
                "translatable": 1,
                "allow_on_submit": 1,
                "hidden": 0
            },
            {
                "fieldname": "custom_purchase_order_approver_name",
                "label": "Purchase Order Approver Name",
                "fieldtype": "Data",
                "insert_after": "custom_purchase_order_approver",
                "fetch_from": "custom_purchase_order_approver.full_name",
                "depends_on": "eval: doc.workflow_state == \"Pending Approver\"",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_purchase_order_approver",
                "label": "Purchase Order Approver",
                "fieldtype": "Link",
                "insert_after": "schedule_date",
                "options": "User",
                "fetch_from": "request_for_material.request_for_material_approver",
                "depends_on": "eval: doc.workflow_state == \"Pending Approver\"",
                "read_only": 1
            },
            {
                "fieldname": "department_manager",
                "label": "Approver",
                "fieldtype": "Link",
                "insert_after": "purchase_type",
                "options": "User",
                "depends_on": "eval:!['Stock',\"Project\"].includes(doc.purchase_type)",
                "read_only": 1
            },
            {
                "fieldname": "purchase_type",
                "label": "Purchase Type",
                "fieldtype": "Data",
                "insert_after": "dimension_col_break",
                "fetch_from": "one_fm_request_for_purchase.type",
                "translatable": 1
            },
            {
                "fieldname": "authority_signature",
                "label": "Authority Signature",
                "fieldtype": "Signature",
                "insert_after": "signatures",
                "depends_on": "eval: doc.workflow_state == 'Approved';",
                "read_only": 1
            },
            {
                "fieldname": "signatures",
                "label": "Signatures",
                "fieldtype": "Section Break",
                "insert_after": "payment_schedule"
            },
            {
                "fieldname": "quoted_delivery_date",
                "label": "Quoted Delivery Date",
                "fieldtype": "Date",
                "insert_after": "supplier_quotation_attachment",
                "hidden": 1
            },
            {
                "fieldname": "supplier_quotation_attachment",
                "label": "Supplier Quotation Attachment",
                "fieldtype": "Attach",
                "insert_after": "quotation"
            },
            {
                "fieldname": "quotation",
                "label": "Quotation Number",
                "fieldtype": "Data",
                "insert_after": "request_for_material",
                "hidden": 1,
                "translatable": 1
            },
            {
                "fieldname": "request_for_material",
                "label": "Request for Material",
                "fieldtype": "Link",
                "insert_after": "one_fm_request_for_purchase",
                "options": "Request for Material",
                "in_standard_filter": 1,
                "read_only": 1
            },
            {
                "fieldname": "other_conditions",
                "label": "Notes",
                "fieldtype": "Text Editor",
                "insert_after": "terms",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_warehouse_location",
                "label": "Warehouse Location",
                "fieldtype": "Small Text",
                "insert_after": "set_warehouse",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_warehouse_contact_person",
                "label": "Warehouse Contact Person",
                "fieldtype": "Data",
                "insert_after": "one_fm_warehouse_location",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_other_documents_required",
                "label": "Other Documents Required",
                "fieldtype": "Select",
                "insert_after": "one_fm_certificate_of_origin_required",
                "options": "\nYes\nNo",
                "default": "No",
                "depends_on": "eval:doc.one_fm_type_of_purchase=='Import'",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_po_document_cb",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_other_documents_required"
            },
            {
                "fieldname": "one_fm_details_of_other_documents",
                "label": "Details of Other Documents",
                "fieldtype": "Small Text",
                "insert_after": "one_fm_po_document_cb",
                "depends_on": "eval:doc.one_fm_other_documents_required=='Yes'",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_type_of_purchase",
                "label": "Type of Purchase",
                "fieldtype": "Select",
                "insert_after": "one_fm_po_document_section",
                "options": "\nLocal\nImport",
                "in_standard_filter": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_po_document_section",
                "label": "",
                "fieldtype": "Section Break",
                "insert_after": "amended_from"
            },
            {
                "fieldname": "one_fm_certificate_of_origin_required",
                "label": "Certificate of Origin Required",
                "fieldtype": "Select",
                "insert_after": "one_fm_type_of_purchase",
                "options": "\nYes\nNo",
                "depends_on": "eval:doc.one_fm_type_of_purchase=='Import'",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_contact_person_email",
                "label": "Contact Person Email",
                "fieldtype": "Data",
                "insert_after": "one_fm_contact_person_phone",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_contact_person_phone",
                "label": "Contact Person Phone",
                "fieldtype": "Data",
                "insert_after": "one_fm_warehouse_contact_person",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_request_for_purchase",
                "label": "Request for Purchase",
                "fieldtype": "Link",
                "insert_after": "supplier",
                "options": "Request for Purchase",
                "in_standard_filter": 1,
                "read_only": 1
            },
            {
                "fieldname": "item_request",
                "label": "Item Request",
                "fieldtype": "Link",
                "insert_after": "company",
                "options": "Item Request",
                "hidden": 1
            },
            {
                "fieldname": "custom_contact_person",
                "label": "Contact Person",
                "fieldtype": "Data",
                "insert_after": "shipping_address_display",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_contact_number",
                "label": "Contact Number",
                "fieldtype": "Data",
                "insert_after": "custom_contact_person",
                "allow_on_submit": 1,
            },
            
        ]
    }
