def get_shift_assignment_custom_fields():
    return {
        "Shift Assignment": [
            {
                "fieldname": "custom_day_off_ot",
                "fieldtype": "Check",
                "label": "Day Off OT",
                "insert_after": "replaced_shift_assignment"
            },
            {
                "fieldname": "custom_employment_type",
                "fieldtype": "Link",
                "label": "Employment Type",
                "insert_after": "employee_name",
                "options": "Employment Type",
                "fetch_from": "employee.employment_type",
                "read_only": 1
            },
            {
                "fieldname": "replaced_shift_assignment",
                "fieldtype": "Link",
                "label": "Replaced Shift Assignment",
                "insert_after": "is_replaced",
                "options": "Shift Assignment"
            },
            {
                "fieldname": "is_replaced",
                "fieldtype": "Check",
                "label": "Is Replaced",
                "insert_after": "employee_schedule",
                "depends_on": "eval: doc.is_replaced;",
                "read_only": 1
            },
            {
                "fieldname": "employee_schedule",
                "fieldtype": "Link",
                "label": "Employee Schedule",
                "insert_after": "site_location",
                "options": "Employee Schedule",
                "read_only": 1
            },
            {
                "fieldname": "site_location",
                "fieldtype": "Link",
                "label": "Site Location",
                "insert_after": "shift_classification",
                "options": "Location",
                "fetch_from": "site.site_location",
                "fetch_if_empty": 1
            },
            {
                "fieldname": "shift_classification",
                "fieldtype": "Data",
                "label": "Shift Classification",
                "insert_after": "status",
                "fetch_from": "shift.shift_classification",
                "fetch_if_empty": 1,
                "depends_on": "shift",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "end_datetime",
                "fieldtype": "Datetime",
                "label": "End Datetime",
                "insert_after": "start_datetime",
                "read_only": 1
            },
            {
                "fieldname": "start_datetime",
                "fieldtype": "Datetime",
                "label": "Start Datetime",
                "insert_after": "end_date",
                "read_only": 1
            },
            {
                "fieldname": "check_out_site",
                "fieldtype": "Link",
                "label": "Check Out Site",
                "insert_after": "column_break_19",
                "options": "Location",
                "fetch_from": "shift_request.check_out_site"
            },
            {
                "fieldname": "column_break_19",
                "fieldtype": "Column Break",
                "insert_after": "check_in_site"
            },
            {
                "fieldname": "check_in_site",
                "fieldtype": "Link",
                "label": "Check In Site",
                "insert_after": "site_request",
                "options": "Location",
                "fetch_from": "shift_request.check_in_site"
            },
            {
                "fieldname": "site_request",
                "fieldtype": "Section Break",
                "label": "Site Request",
                "insert_after": "roster_type",
                "depends_on": "eval: doc.shift_request;"
            },
            {
                "fieldname": "roster_type",
                "fieldtype": "Select",
                "label": "Roster Type",
                "insert_after": "post_abbrv",
                "options": "Basic\nOver-Time",
                "translatable": 1
            },
            {
                "fieldname": "post_abbrv",
                "fieldtype": "Data",
                "label": "Post Abbreviation",
                "insert_after": "operations_role",
                "fetch_from": "operations_role.post_abbrv",
                "translatable": 1
            },
            {
                "fieldname": "post_type",
                "fieldtype": "Link",
                "label": "Post Type",
                "insert_after": "check_out_site",
                "options": "Operations Role"
            },
            {
                "fieldname": "operations_role",
                "fieldtype": "Link",
                "label": "Operations Role",
                "insert_after": "amended_from",
                "options": "Operations Role"
            },
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "label": "Project",
                "insert_after": "site",
                "options": "Project",
                "fetch_from": "shift.project"
            },
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "label": "Site",
                "insert_after": "shift_type",
                "options": "Operations Site",
                "allow_on_submit": 1,
                "fetch_from": "shift.site"
            },
            {
                "fieldname": "shift",
                "fieldtype": "Link",
                "label": "Shift",
                "insert_after": "department",
                "options": "Operations Shift"
            }
        ]
    }