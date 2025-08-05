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
                "options": " \nAssign Day Off\nAssign Unrostered Employee\nReplace Existing Assignment\nUpdate Existing Assignment\nDay Off Overtime",
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
                "depends_on": "eval:doc.purpose != 'Assign Day Off'"
            },
            {
                "fieldname": "roster_type",
                "fieldtype": "Select",
                "label": "Roster Type",
                "insert_after": "operations_role",
                "options": "Basic\nOver-Time",
                "depends_on": "eval:doc.purpose != 'Assign Day Off';",
                "translatable": 1
            },
            {
                "fieldname": "operations_role",
                "fieldtype": "Link",
                "label": "Operations Role",
                "insert_after": "to_date",
                "options": "Operations Role",
                "fetch_if_empty": 1,
                "depends_on": "eval:doc.purpose != 'Assign Day Off';",
                "mandatory_depends_on": "eval:doc.purpose != 'Assign Day Off';"
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
                "fieldname": "shift_approver",
                "fieldtype": "Link",
                "label": "Shift Approver",
                "insert_after": "company_name",
                "options": "User",
                "fetch_from": "approver",
                "hidden": 1,
                "read_only": 1
            },
            {
                "fieldname": "shift",
                "fieldtype": "Link",
                "label": "Shift",
                "insert_after": "operations_shift",
                "options": "Shift Type",
                "fetch_from": "operations_shift.shift_type",
                "depends_on": "eval:doc.purpose != 'Assign Day Off';",
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
                "depends_on": "eval:doc.purpose != 'Assign Day Off'"
            },
            {
                "fieldname": "operations_shift",
                "fieldtype": "Link",
                "label": "Operations Shift",
                "insert_after": "custom_replaced_employee_name",
                "options": "Operations Shift",
                "fetch_from": "employee.shift",
                "fetch_if_empty": 1,
                "depends_on": "eval:doc.purpose != 'Assign Day Off';",
                "mandatory_depends_on": "eval:doc.purpose != 'Assign Day Off';",
                "reqd": 1
            },
            {
                "fieldname": "custom_shift_approvers",
                "fieldtype": "Table MultiSelect",
                "label": "Shift Approvers",
                "insert_after": "shift_approver",
                "options": "Shift Request Approvers",
                "read_only": 1
            }
        ]
    }
