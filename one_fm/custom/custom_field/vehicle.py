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
                "options": "\nOwned\nLeased\nSubcontractor",
                "translatable": 1,
                "reqd": 1
            },
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "insert_after": "one_fm_vehicle_category",
                "options": "\nVHL-S-.####\nVHL-L-.####\nVHL-.####",
                "no_copy": 1,
                "default": "VHL-.####",
                "read_only": 1,
                "print_hide": 1
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
            },
            {
                "fieldname": "seats",
                "fieldtype": "Int",
                "label": "Seats",
                "insert_after": "doors",
                "reqd": 1
            },
            {
                "fieldname": "transport_stop_vehicle",
                "fieldtype": "Check",
                "label": "Transport Stop Vehicle",
                "insert_after": "image",
                "default": 0
            },
            {
                "fieldname": "custom_branding_details",
                "fieldtype": "Section Break",
                "label": "Branding Details",
                "insert_after": "one_fm_documents_cb",
            },
            {
                "fieldname": "custom_branding_application_date",
                "fieldtype": "Date",
                "label": "Branding Application Date",
                "insert_after": "custom_branding_details",
            },
            {
                "fieldname": "custom_branding_image",
                "fieldtype": "Attach Image",
                "label": "Branding Image",
                "insert_after": "custom_branding_application_date",
            },
            {
                "fieldname": "custom_column_break_nnxbp",
                "fieldtype": "Column Break",
                "label": "",
                "insert_after": "custom_branding_image",
            },
            {
                "fieldname": "custom_branding_registration_issue_date",
                "fieldtype": "Date",
                "label": "Branding Registration Issue Date",
                "insert_after": "custom_column_break_nnxbp",
            },
            {
                "fieldname": "custom_branding_registration_expiration_date",
                "fieldtype": "Date",
                "label": "Branding Registration Expiration Date",
                "insert_after": "custom_branding_registration_issue_date",
            },
            {
                "fieldname": "custom_status",
                "fieldtype": "Select",
                "label": "Status",
                "insert_after": "one_fm_vehicle_status",
                "options": "\nActive\nInactive",
                "default": "Active",
                "reqd": 1,
                "translatable": 1,
            },
            {
                "fieldname": "custom_handover_date",
                "fieldtype": "Date",
                "label": "Handover Date",
                "insert_after": "employee",
                "reqd": 1,
            },
            {
                "fieldname": "custom_section_break_ufvnv",
                "fieldtype": "Section Break",
                "label": "",
                "insert_after": "custom_branding_registration_expiration_date",
            },
            {
                "fieldname": "custom_vehicle_custodian_history",
                "fieldtype": "Table",
                "label": "Vehicle Custodian History",
                "insert_after": "custom_section_break_ufvnv",
                "options": "Vehicle Custodian History",
                "read_only": 1,
            },
            # WI-002000. Whether "seats" counts the driver is per vehicle, so the
            # passenger limit is derived rather than assumed: capacity = seats - 1
            # when the driver's seat is included, seats when it is not. Both are
            # applied exactly as exported from the BA site, including
            # insert_after "amended_from", which puts the read-only capacity at the
            # foot of the form.
            {
                "fieldname": "custom_includes_driver_seat",
                "fieldtype": "Check",
                "label": "Includes Driver Seat",
                "insert_after": "seats",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_max_passenger_capacity",
                "fieldtype": "Int",
                "label": "Max Passenger Capacity",
                "insert_after": "amended_from",
                "read_only": 1,
                "allow_on_submit": 1,
            },
        ]
    }