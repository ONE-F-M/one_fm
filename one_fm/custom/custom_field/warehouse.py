def get_warehouse_custom_fields():
    return {
        "Warehouse": [
            {
                "fieldname": "warehouse_code",
                "fieldtype": "Data",
                "label": "Warehouse Code",
                "insert_after": "warehouse_name",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_store_keeper",
                "fieldtype": "Link",
                "label": "Store Keeper",
                "insert_after": "warehouse_code",
                "options": "Employee",
                "ignore_user_permissions": 1
            },
            {
                "fieldname": "column_break_c21su",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_store_keeper"
            },
            {
                "fieldname": "status",
                "fieldtype": "Select",
                "label": "Status",
                "insert_after": "column_break_c21su",
                "options": "Enable\nDisable\nFreeze"
            },
            {
                "fieldname": "cost_center",
                "fieldtype": "Link",
                "label": "Cost Center",
                "insert_after": "parent_warehouse",
                "options": "Cost Center"
            },
            {
                "fieldname": "allow_zero_valuation_rate",
                "fieldtype": "Check",
                "label": "Allow Zero Valuation Rate",
                "insert_after": "cost_center",
                "description": "If this field is checked, all the items in this warehouse will be brought in at zero valuation rate."
            },
            {
                "fieldname": "project_and_department_sb",
                "fieldtype": "Section Break",
                "insert_after": "company"
            },
            {
                "fieldname": "one_fm_is_project_warehouse",
                "fieldtype": "Check",
                "label": "Is Project Warehouse",
                "insert_after": "project_and_department_sb"
            },
            {
                "fieldname": "one_fm_project",
                "fieldtype": "Link",
                "label": "Project",
                "insert_after": "one_fm_is_project_warehouse",
                "options": "Project",
                "depends_on": "one_fm_is_project_warehouse",
                "mandatory_depends_on": "one_fm_is_project_warehouse"
            },
            {
                "fieldname": "one_fm_site",
                "fieldtype": "Link",
                "label": "Site",
                "insert_after": "one_fm_project",
                "options": "Operations Site",
                "depends_on": "one_fm_is_project_warehouse"
            },
            {
                "fieldname": "one_fm_location",
                "fieldtype": "Link",
                "label": "Location",
                "insert_after": "one_fm_site",
                "options": "Location"
            },
            {
                "fieldname": "column_break_2azq1",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_location"
            },
            {
                "fieldname": "is_uniform_warehouse",
                "fieldtype": "Check",
                "label": "Is Uniform Warehouse",
                "insert_after": "column_break_2azq1"
            },
            {
                "fieldname": "department",
                "fieldtype": "Link",
                "label": "Department",
                "insert_after": "is_uniform_warehouse",
                "options": "Department"
            }
        ]
    }
