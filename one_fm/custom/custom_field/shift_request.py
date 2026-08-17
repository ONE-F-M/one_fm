def get_shift_request_custom_fields():
    return {
        "Shift Request": [
            {
                "fieldname": "custom_replaced_employee_name",
                "fieldtype": "Data",
                "label": "Replaced Employee Name",
                "insert_after": "replaced_employee",
                "fetch_from": "replaced_employee.employee_name",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "replaced_employee",
                "fieldtype": "Link",
                "label": "Replaced Employee",
                "insert_after": "purpose",
                "options": "Employee",
                "depends_on": "eval:doc.purpose == 'Replace Existing Assignment';",
                "mandatory_depends_on": "eval:doc.purpose == 'Replace Existing Assignment';"
            },
            {
                "fieldname": "purpose",
                "fieldtype": "Select",
                "label": "Purpose",
                "insert_after": "employee_name",
                "options": " \nAssign Day Off\nAssign Client Day Off\nAssign Unrostered Employee\nReplace Existing Assignment\nUpdate Existing Assignment\nDay Off Overtime",
                "reqd": 1,
                "translatable": 1
            },
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "label": "Project",
                "insert_after": "site",
                "options": "Project",
                "fetch_from": "site.project",
                "fetch_if_empty": 1,
                "read_only": 1
            },
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "label": "Site",
                "insert_after": "shift",
                "options": "Operations Site",
                "fetch_from": "operations_shift.site",
                "depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
            },
            {
                "fieldname": "roster_type",
                "fieldtype": "Select",
                "label": "Roster Type",
                "insert_after": "operations_role",
                "options": "Basic\nOver-Time",
                "depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
                "translatable": 1
            },
            {
                "fieldname": "operations_role",
                "fieldtype": "Link",
                "label": "Operations Role",
                "insert_after": "to_date",
                "options": "Operations Role",
                "fetch_if_empty": 1,
                "depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
                "mandatory_depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)'
            },
            {
                "fieldname": "company_name",
                "fieldtype": "Link",
                "label": "Company Name",
                "insert_after": "roster_type",
                "options": "Company",
                "fetch_from": "employee.company",
                "read_only": 1
            },
            {
                "fieldname": "shift",
                "fieldtype": "Link",
                "label": "Shift",
                "insert_after": "operations_shift",
                "options": "Shift Type",
                "fetch_from": "operations_shift.shift_type",
                "depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
                "read_only": 1
            },
            {
                "fieldname": "checkout_radius",
                "fieldtype": "Data",
                "label": "CheckOut Radius",
                "insert_after": "checkout_latitude",
                "fetch_from": "check_in_site.geofence_radius",
                "hidden": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "checkin_radius",
                "fieldtype": "Data",
                "label": "Checkin Radius",
                "insert_after": "checkin_latitude",
                "fetch_from": "check_in_site.geofence_radius",
                "hidden": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "checkout_longitude",
                "fieldtype": "Data",
                "label": "CheckOut Longitude",
                "insert_after": "check_out_site",
                "fetch_from": "check_out_site.longitude",
                "hidden": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "checkout_latitude",
                "fieldtype": "Data",
                "label": "CheckOut Latitude",
                "insert_after": "checkout_longitude",
                "fetch_from": "check_out_site.latitude",
                "hidden": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "checkin_latitude",
                "fieldtype": "Data",
                "label": "Checkin Latitude",
                "insert_after": "checkin_longitude",
                "fetch_from": "check_in_site.latitude",
                "hidden": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "checkin_longitude",
                "fieldtype": "Data",
                "label": "Checkin Longitude",
                "insert_after": "check_in_site",
                "fetch_from": "check_in_site.longitude",
                "hidden": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "checkout_map_html",
                "fieldtype": "HTML",
                "label": "Checkout Map HTML",
                "insert_after": "checkout_radius",
                "depends_on": "eval: doc.check_out_site;"
            },
            {
                "fieldname": "checkin_map_html",
                "fieldtype": "HTML",
                "label": "Checkin Map HTML",
                "insert_after": "checkin_radius",
                "depends_on": "eval: doc.check_in_site;"
            },
            {
                "fieldname": "checkout_map",
                "fieldtype": "Geolocation",
                "label": "Checkout Map",
                "insert_after": "checkout_map_html",
                "hidden": 1
            },
            {
                "fieldname": "checkin_map",
                "fieldtype": "Geolocation",
                "label": "Checkin Map",
                "insert_after": "checkout_map",
                "hidden": 1
            },
            {
                "fieldname": "title",
                "fieldtype": "Data",
                "label": "title",
                "insert_after": "workflow_state",
                "fetch_from": "employee.employee_name",
                "hidden": 1,
                "read_only": 1
            },
            {
                "fieldname": "update_request",
                "fieldtype": "Check",
                "label": "Update Request",
                "insert_after": "shift_approver",
                "depends_on": "eval:doc.docstatus > 0",
                "allow_on_submit": 1,
                "read_only": 1
            },
            {
                "fieldname": "column_break_15",
                "fieldtype": "Column Break",
                "insert_after": "checkin_map_html"
            },
            {
                "fieldname": "check_out_site",
                "fieldtype": "Link",
                "label": "Check Out Site",
                "insert_after": "column_break_15",
                "options": "Location",
                "fetch_from": "site.site_location",
                "fetch_if_empty": 1
            },
            {
                "fieldname": "check_in_site",
                "fieldtype": "Link",
                "label": "Check In Site",
                "insert_after": "site_request",
                "options": "Location",
                "fetch_from": "site.site_location",
                "fetch_if_empty": 1
            },
            {
                "fieldname": "site_request",
                "fieldtype": "Section Break",
                "label": "Site Request",
                "insert_after": "amended_from",
                "depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
            },
            {
                "fieldname": "operations_shift",
                "fieldtype": "Link",
                "label": "Operations Shift",
                "insert_after": "custom_replaced_employee_name",
                "options": "Operations Shift",
                "fetch_from": "employee.shift",
                "fetch_if_empty": 1,
                "depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
                "mandatory_depends_on": 'eval:!["Assign Day Off", "Assign Client Day Off"].includes(doc.purpose)',
                "reqd": 1
            },
           {
                "label": "Approval",
                "fieldname": "custom_approval",
                "insert_after": "amended_from",
                "fieldtype": "Section Break"
            },
            {
                "label": "Reports To",
                "fieldname": "custom_reports_to",
                "insert_after": "custom_approval",
                "fieldtype": "Link",
                "options": "Employee",
                "fetch_from": "employee.reports_to",
                "read_only": 1,
                "ignore_user_permissions": 1
            },
            {
                "label": "Reports To User",
                "fieldname": "custom_reports_to_user",
                "insert_after": "custom_reports_to",
                "fieldtype": "Link",
                "options": "User",
                "fetch_from": "custom_reports_to.user_id",
                "read_only": 1,
                "ignore_user_permissions": 1
            },
            {
                "label": "",
                "fieldname": "custom_column_break_ggqao",
                "insert_after": "custom_reports_to_user",
                "fieldtype": "Column Break"
            },
            {
                "label": "Project Manager",
                "fieldname": "custom_project_manager",
                "insert_after": "custom_column_break_ggqao",
                "fieldtype": "Link",
                "options": "Employee",
                "fetch_from": "project.project_manager",
                "read_only": 1,
                "ignore_user_permissions": 1
            },
            {
                "label": "Project Manager User",
                "fieldname": "custom_project_manager_user",
                "insert_after": "custom_project_manager",
                "fieldtype": "Link",
                "fetch_from": "custom_project_manager.user_id",
                "read_only": 1,
                "options": "User",
                "ignore_user_permissions": 1
             },
            {
                "fieldname": "reason",
                "fieldtype": "Small Text",
                "insert_after": "status",
                "label": "Reason",
                "reqd": 1,
                "translatable": 1
            },
            # WI-001834: the approver sees how timing varies across the requested range
            # before approving it. Both fields hang off the preview being non-empty, so a
            # range that is all default days shows nothing at all - which is the third
            # acceptance criterion, and keeps the form as it is today for the common case.
            {
                "fieldname": "custom_section_break_z4s37",
                "fieldtype": "Section Break",
                "insert_after": "custom_project_manager_user",
                "label": "Shift Preview",
                "depends_on": "eval:doc.custom_shift_preview && doc.custom_shift_preview.length"
            },
            {
                "fieldname": "custom_shift_preview",
                "fieldtype": "Table",
                "insert_after": "custom_section_break_z4s37",
                "label": "Shift Preview",
                "options": "Shift Preview",
                # Read-only on the grid rather than on each of the child doctype's three
                # fields: one property instead of three, and the rows are system-derived, so
                # there is nothing here for a requester to fill in.
                "read_only": 1,
                "depends_on": "eval:doc.custom_shift_preview && doc.custom_shift_preview.length",
                "description": "Filled automatically when the requested range covers a day whose Operations Shift timing differs from the default."
            }
        ]
    }
