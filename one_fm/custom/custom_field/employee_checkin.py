def get_employee_checkin_custom_fields():
    return {
        "Employee Checkin": [
            {
                "fieldname": "replaced_employee_checkin",
                "fieldtype": "Link",
                "insert_after": "is_replaced",
                "label": "Replaced Employee Checkin",
                "options": "Shift Assignment",
                "depends_on": "eval: doc.is_replaced;"
            },
            {
                "fieldname": "is_replaced",
                "fieldtype": "Check",
                "insert_after": "company",
                "label": "Is Replaced",
                "read_only": 1
            },
            {
                "fieldname": "source",
                "fieldtype": "Select",
                "insert_after": "employee_checkin_issue",
                "label": "Source",
                "options": "\nMobile App\nMobile Web\nCheck-in Form\nFrappe Page",
                "default": "Check-in Form",
                "translatable": 1
            },
            {
                "fieldname": "post_abbrv",
                "fieldtype": "Data",
                "insert_after": "operations_role",
                "label": "Post Abbrv",
                "fetch_from": "operations_role.post_abbrv",
                "fetch_if_empty": 1,
                "read_only": 1
            },
            {
                "fieldname": "operations_role",
                "fieldtype": "Link",
                "insert_after": "column_break_15",
                "label": "Operations Role",
                "options": "Operations Role",
                "fetch_from": "shift_assignment.operations_role",
                "fetch_if_empty": 1,
                "read_only": 1
            },
            {
                "fieldname": "company",
                "fieldtype": "Link",
                "insert_after": "project",
                "label": "Company",
                "options": "Company",
                "fetch_from": "shift_assignment.company",
                "fetch_if_empty": 1,
                "read_only": 1
            },
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "insert_after": "operations_site",
                "label": "Project",
                "options": "Project",
                "fetch_from": "shift_assignment.project",
                "fetch_if_empty": 1,
                "read_only": 1
            },
            {
                "fieldname": "operations_site",
                "fieldtype": "Link",
                "insert_after": "operations_shift",
                "label": "Operations Site",
                "options": "Operations Site",
                "fetch_from": "shift_assignment.site",
                "fetch_if_empty": 1,
                "read_only": 1
            },
            {
                "fieldname": "roster_type",
                "fieldtype": "Data",
                "insert_after": "post_abbrv",
                "label": "Roster Type",
                "fetch_from": "shift_assignment.roster_type",
                "fetch_if_empty": 1,
                "translatable": 1
            },
            {
                "fieldname": "date",
                "fieldtype": "Date",
                "insert_after": "time",
                "label": "Date",
                "in_standard_filter": 1,
                "read_only": 1
            },
            {
                "fieldname": "employee_checkin_issue",
                "fieldtype": "Link",
                "insert_after": "actual_time",
                "label": "Employee Checkin Issue",
                "options": "Employee Checkin Issue",
                "read_only": 1
            },
            {
                "fieldname": "early_exit",
                "fieldtype": "Check",
                "insert_after": "late_entry",
                "label": "Early Exit",
                "read_only": 1
            },
            {
                "fieldname": "late_entry",
                "fieldtype": "Check",
                "insert_after": "shift",
                "label": "Late Entry",
                "default": "0",
                "read_only": 1
            },
            {
                "fieldname": "shift_assignment",
                "fieldtype": "Link",
                "insert_after": "shift_details",
                "label": "Shift Assignment",
                "options": "Shift Assignment"
            },
            {
                "fieldname": "actual_time",
                "fieldtype": "Datetime",
                "insert_after": "shift_permission",
                "label": "Actual Time",
                "default": "now",
                "read_only": 1
            },
            {
                "fieldname": "shift_permission",
                "fieldtype": "Link",
                "insert_after": "shift_type",
                "label": "Shift Permission",
                "options": "Shift Permission"
            },
            {
                "fieldname": "column_break_15",
                "insert_after": "replaced_employee_checkin",
                "fieldtype": "Column Break"
            },
            {
                "label": "Shift Type",
                "fieldname": "shift_type",
                "insert_after": "roster_type",
                "fieldtype": "Data",
                "fetch_from": "shift_assignment.shift_type",
                "fetch_if_empty": 1,
                "depends_on": "eval:doc.shift_assignment",
                "read_only": 1,
                "ignore_user_permissions": 1
            },
            {
                "label": "Shift Details",
                "fieldname": "shift_details",
                "insert_after": "shift_actual_end",
                "fieldtype": "Section Break"
            },
            {
                "label": "Operations Shift",
                "fieldname": "operations_shift",
                "insert_after": "shift_assignment",
                "fieldtype": "Link",
                "options": "Operations Shift",
                "fetch_from": "shift_assignment.shift",
                "fetch_if_empty": 1,
                "depends_on": "eval:doc.shift_assignment",
                "read_only": 1,
                "ignore_user_permissions": 1
            }
        ]
    }
