def get_vehicle_custom_fields():
    return {
        "Vehicle": [
            {
                "fieldname": "one_fm_purpose_of_use",
                "fieldtype": "Select",
                "label": "Purpose of Use",
                "insert_after": "location",
                "options": "\nPersonal\nGeneral",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_vehicle_status",
                "fieldtype": "Select",
                "label": "Vehicle Status",
                "insert_after": "one_fm_purpose_of_use",
                "options": "\nBrand New\nUsed",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_year_of_made",
                "fieldtype": "Data",
                "label": "Year of Made",
                "insert_after": "model",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_fuel_capacity",
                "fieldtype": "Float",
                "label": "Fuel Capacity",
                "insert_after": "fuel_type"
            },
            {
                "fieldname": "one_fm_milage",
                "fieldtype": "Float",
                "label": "Milage in KM",
                "insert_after": "uom"
            },
            {
                "fieldname": "one_fm_registry_expiration_date",
                "fieldtype": "Date",
                "label": "Registry Expiration Date",
                "insert_after": "employee"
            },
            {
                "fieldname": "one_fm_documents",
                "fieldtype": "Section Break",
                "label": "Documents",
                "insert_after": "amended_from",
                "collapsible": 1
            },
            {
                "fieldname": "one_fm_registration_document",
                "fieldtype": "Attach",
                "label": "Registration Document",
                "insert_after": "one_fm_documents"
            },
            {
                "fieldname": "one_fm_handover_document",
                "fieldtype": "Attach",
                "label": "Handover Document",
                "insert_after": "one_fm_registration_document"
            },
            {
                "fieldname": "one_fm_documents_cb",
                "fieldtype": "Column Break",
                "label": "",
                "insert_after": "one_fm_handover_document"
            },
            {
                "fieldname": "one_fm_vehicle_photo",
                "fieldtype": "Attach",
                "label": "Vehicle Photo",
                "insert_after": "one_fm_documents_cb"
            },
            {
                "fieldname": "one_fm_vehicle_category",
                "fieldtype": "Select",
                "label": "Vehicle Category",
                "insert_after": "license_plate",
                "options": "\nOwned\nLeased",
                "translatable": 1,
                "reqd": 1
            },
            {
                "fieldname": "one_fm_vehicle_type",
                "fieldtype": "Link",
                "label": "Vehicle Type",
                "insert_after": "make",
                "options": "Vehicle Type",
                "reqd": 1
            },
            {
                "fieldname": "one_fm_vehicle_qr_code",
                "fieldtype": "Data",
                "label": "QR Code",
                "insert_after": "one_fm_year_of_made",
                "depends_on": "eval:!doc.__islocal"
            },
            {
                "fieldname": "vehicle_leasing_contract",
                "fieldtype": "Link",
                "label": "Vehicle Leasing Contract",
                "insert_after": "one_fm_vehicle_category",
                "options": "Vehicle Leasing Contract",
                "depends_on": "eval:doc.one_fm_vehicle_category == 'Leased'"
            },
            {
                "fieldname": "vehicle_leasing_details",
                "fieldtype": "Link",
                "label": "Vehicle Leasing Details",
                "insert_after": "vehicle_leasing_contract",
                "options": "Vehicle Leasing Contract Item",
                "depends_on": "vehicle_leasing_contract"
            },
            {
                "fieldname": "image",
                "fieldtype": "Attach Image",
                "label": "Image"
            }
        ]
    }