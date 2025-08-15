def get_attendance_custom_fields():
    return {
        "Attendance": [
            {
                "fieldname": "custom_employment_type",
                "fieldtype": "Link",
                "insert_after": "employee_name",
                "label": "Employment Type",
                "options": "Employment Type",
                "read_only": 1
            },
            {
                "fieldname": "reference_doctype",
                "fieldtype": "Link",
                "insert_after": "references",
                "label": "Reference Doctype",
                "options": "DocType"
            },
            {
                "fieldname": "reference_docname",
                "fieldtype": "Dynamic Link",
                "insert_after": "column_break_nahps",
                "label": "Reference Docname",
                "options": "reference_doctype",
                "depends_on": "eval:doc.reference_doctype"
            },
            {
                "fieldname": "column_break_nahps",
                "fieldtype": "Column Break",
                "insert_after": "reference_doctype"
            },
            {
                "fieldname": "references",
                "fieldtype": "Section Break",
                "insert_after": "comment",
                "label": "References"
            },
            {
                "fieldname": "sale_item",
                "fieldtype": "Data",
                "insert_after": "post_type",
                "label": "Sale Item",
                "depends_on": "eval:doc.operations_role",
                "read_only": 1
            },
            {
                "fieldname": "comment",
                "fieldtype": "Small Text",
                "insert_after": "attendance_comment",
                "label": "Comment"
            },
            {
                "fieldname": "attendance_comment",
                "fieldtype": "Section Break",
                "insert_after": "day_off_ot",
                "label": "Attendance Comment"
            },
            {
                "fieldname": "timesheet",
                "fieldtype": "Link",
                "insert_after": "project",
                "label": "Timesheet",
                "options": "Timesheet",
                "read_only": 1
            },
            {
                "fieldname": "shift_assignment",
                "fieldtype": "Link",
                "insert_after": "section_break_17",
                "label": "Shift Assignment",
                "options": "Shift Assignment"
            },
            {
                "fieldname": "day_off_ot",
                "fieldtype": "Check",
                "insert_after": "sale_item",
                "label": "Day Off OT",
                "read_only": 1
            },
            {
                "fieldname": "roster_type",
                "fieldtype": "Select",
                "insert_after": "post_abbrv",
                "label": "Roster Type",
                "options": "Basic\nOver-Time",
                "default": "Basic",
                "in_standard_filter": 1
            },
            {
                "fieldname": "operations_shift",
                "fieldtype": "Link",
                "insert_after": "shift_assignment",
                "label": "Operations Shift",
                "options": "Operations Shift",
                "read_only": 1
            },
            {
                "fieldname": "post_abbrv",
                "fieldtype": "Data",
                "insert_after": "operations_role",
                "label": "Post Abbrv",
                "read_only": 1
            },
            {
                "fieldname": "post_type",
                "fieldtype": "Link",
                "insert_after": "roster_type",
                "label": "Post Type",
                "options": "Operations Role",
                "read_only": 1
            },
            {
                "fieldname": "operations_role",
                "fieldtype": "Link",
                "insert_after": "column_break_21",
                "label": "Operations Role",
                "options": "Operations Role",
                "read_only": 1
            },
            {
                "fieldname": "column_break_21",
                "fieldtype": "Column Break",
                "insert_after": "timesheet"
            },
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "insert_after": "site",
                "label": "Project",
                "options": "Project",
                "read_only": 1
            },
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "insert_after": "operations_shift",
                "label": "Site",
                "options": "Operations Site",
                "read_only": 1
            },
            {
                "fieldname": "section_break_17",
                "fieldtype": "Section Break",
                "insert_after": "early_exit"
            },
            {
                "fieldname": "is_unscheduled",
                "fieldtype": "Check",
                "insert_after": "reference",
                "label": "Has No Shift Assignment"
            }
        ]
    }
