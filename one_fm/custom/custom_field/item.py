def get_item_custom_fields():
    return {
        "Item": [
            {
                "fieldname": "hub_sync_id",
                "fieldtype": "Data",
                "insert_after": "workflow_state",
                "label": "Hub Sync ID",
                "hidden": 1,
                "read_only": 1,
                "unique": 1,
                "no_copy": 1
            },
            {
                "fieldname": "description1",
                "fieldtype": "Data",
                "insert_after": "item_descriptions",
                "label": "Description1",
                "hidden": 1
            },
            {
                "fieldname": "description2",
                "fieldtype": "Data",
                "insert_after": "description1",
                "label": "Description2",
                "hidden": 1
            },
            {
                "label": "Description3",
                "fieldname": "description3",
                "insert_after": "description2",
                "fieldtype": "Data",
                "hidden": 1
            },
            {
                "label": "Description4",
                "fieldname": "description4",
                "insert_after": "description3",
                "fieldtype": "Data",
                "hidden": 1
            },
            {
                "label": "Description5",
                "fieldname": "description5",
                "insert_after": "description4",
                "fieldtype": "Data",
                "hidden": 1
            },
            {
                "label": "Item Barcode",
                "fieldname": "item_barcode_html",
                "insert_after": "stock_uom",
                "fieldtype": "HTML"
            },
            {
                "label": "Item QRcode",
                "fieldname": "item_qrcode_html",
                "insert_after": "item_barcode_html",
                "fieldtype": "HTML"
            },
            {
                "label": "Group",
                "fieldname": "subitem_group",
                "insert_after": "parent_item_group",
                "fieldtype": "Link",
                "options": "Item Group",
                "reqd": 1
            },
            {
                "label": "Group",
                "fieldname": "parent_item_group",
                "insert_after": "item_name",
                "fieldtype": "Link",
                "options": "Item Group",
                "default": "All Item Groups",
                "hidden": 1
            },
            {
                "label": "Item ID",
                "fieldname": "item_id",
                "insert_after": "item_group",
                "fieldtype": "Data",
                "read_only": 1
            },
            {
                "label": "Item Barcode",
                "fieldname": "item_barcode",
                "insert_after": "image",
                "fieldtype": "Barcode"
            },
            {
                "label": "Item Descriptions",
                "fieldname": "item_descriptions",
                "insert_after": "uniform_type_description",
                "fieldtype": "Table",
                "options": "Item Description",
                "hidden": 1
            },
            {
                "label": "Other Description",
                "fieldname": "other_description",
                "insert_after": "description",
                "fieldtype": "Data"
            },
            {
                "label": "Final Description",
                "fieldname": "final_description",
                "insert_after": "description5",
                "fieldtype": "Data",
                "hidden": 1
            },
            {
                "label": "Uniform Type",
                "fieldname": "uniform_type",
                "insert_after": "have_uniform_type_and_description",
                "fieldtype": "Link",
                "options": "Uniform Type",
                "depends_on": "have_uniform_type_and_description",
                "hidden": 1
            },
            {
                "label": "Uniform Type Description",
                "fieldname": "uniform_type_description",
                "insert_after": "uniform_type",
                "fieldtype": "Link",
                "options": "Uniform Type Description",
                "depends_on": "have_uniform_type_and_description",
                "hidden": 1
            },
            {
                "label": "Have Uniform Type and Description",
                "fieldname": "have_uniform_type_and_description",
                "insert_after": "section_break_11",
                "fieldtype": "Check",
                "fetch_from": "0",
                "hidden": 1
            },
            {
                "label": "Is Spare Part",
                "fieldname": "is_spare_part",
                "insert_after": "linked_items",
                "fieldtype": "Check",
                "hidden": 1
            },
            {
                "label": "Is Service",
                "fieldname": "is_service",
                "insert_after": "other_description",
                "fieldtype": "Check",
                "hidden": 1
            },
            {
                "label": "Start Date",
                "fieldname": "start_date",
                "insert_after": "item_life",
                "fieldtype": "Date"
            },
            {
                "label": "End Date",
                "fieldname": "end_date",
                "insert_after": "start_date",
                "fieldtype": "Date"
            },
            {
                "label": "Item Uom",
                "fieldname": "item_uom",
                "insert_after": "item_packaging",
                "fieldtype": "Link",
                "options": "UOM"
            },
            {
                "label": "Item Packaging",
                "fieldname": "item_packaging",
                "insert_after": "item_color",
                "fieldtype": "Link",
                "options": "Packaging"
            },
            {
                "fieldname": "one_fm_descripition_cb",
                "insert_after": "item_uom",
                "fieldtype": "Column Break"
            },
            {
                "label": "Linked Items",
                "fieldname": "linked_items",
                "insert_after": "one_fm_designation",
                "fieldtype": "Link",
                "options": "Item",
                "depends_on": "is_spare_part"
            },
            {
                "label": "Item Type",
                "fieldname": "item_type",
                "insert_after": "is_spare_part",
                "fieldtype": "Link",
                "options": "Item Type",
                "reqd": 1
            },
            {
                "label": "Item Gender",
                "fieldname": "item_gender",
                "insert_after": "one_fm_descripition_cb",
                "fieldtype": "Link",
                "options": "Gender",
                "depends_on": "have_uniform_type_and_description"
            },
            {
                "label": "Item Size",
                "fieldname": "item_size",
                "insert_after": "item_gender",
                "fieldtype": "Data",
                "depends_on": "have_uniform_type_and_description"
            },
            {
                "label": "Project",
                "fieldname": "one_fm_project",
                "insert_after": "final_description",
                "fieldtype": "Link",
                "options": "Project",
                "depends_on": "have_uniform_type_and_description"
            },
            {
                "label": "Designation",
                "fieldname": "one_fm_designation",
                "insert_after": "one_fm_project",
                "fieldtype": "Link",
                "options": "Designation",
                "depends_on": "have_uniform_type_and_description"
            },
            {
                "label": "Item Life",
                "fieldname": "item_life",
                "insert_after": "is_service",
                "fieldtype": "Section Break",
                "collapsible_depends_on": "is_service",
                "depends_on": "is_service"
            },
            {
                "label": "Item Area of Use",
                "fieldname": "item_area_of_use",
                "insert_after": "item_material",
                "fieldtype": "Link",
                "options": "Item Area of Use"
            },
            {
                "label": "Item Color",
                "fieldname": "item_color",
                "insert_after": "item_area_of_use",
                "fieldtype": "Link",
                "options": "Color"
            },
            {
                "label": "Item Material",
                "fieldname": "item_material",
                "insert_after": "item_model",
                "fieldtype": "Link",
                "options": "Item Material"
            },
            {
                "label": "Item Model",
                "fieldname": "item_model",
                "insert_after": "brand",
                "fieldtype": "Link",
                "options": "Item Model"
            },
            {
                "label": "Difference Account",
                "fieldname": "difference_account",
                "insert_after": "item_defaults",
                "fieldtype": "Link",
                "options": "Account"
            },
            {
                "label": "Change Request",
                "fieldname": "change_request",
                "insert_after": "disabled",
                "fieldtype": "Check",
                "read_only": 1,
                "hidden": 1
            }
        ]
    }
