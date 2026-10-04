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
                "label": "Comment",
                "allow_on_submit": 1,
                "read_only_depends_on": "eval:doc.docstatus==1"
            },
            {
                "fieldname": "custom_correction_reason",
                "fieldtype": "Small Text",
                "insert_after": "comment",
                "label": "Correction Reason",
                "read_only": 1,
                "allow_on_submit": 1,
                "no_copy": 1,
                "depends_on": "eval:doc.custom_correction_reason"
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
                "fieldname": "custom_client_event",
                "fieldtype": "Link",
                "insert_after": "timesheet",
                "label": "Client Event",
                "options": "Client Event",
                "fetch_from": "shift_assignment.client_event",
                "read_only": 1
            },
            {
                # WI-001686: what makes Attendance a Connection on Event Staff. Read from
                # the Shift Assignment, the same hop custom_client_event above takes -
                # Client Event has no Event Staff to fetch, it is the far end of a
                # one-to-many.
                "fieldname": "custom_event_staff",
                "fieldtype": "Link",
                "insert_after": "custom_client_event",
                "label": "Event Staff",
                "options": "Event Staff",
                "fetch_from": "shift_assignment.event_staff",
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
                "fieldname": "has_no_shift_assignment",
                "fieldtype": "Check",
                "insert_after": "reference",
                "label": "Has No Shift Assignment"
            }
        ]
    }
