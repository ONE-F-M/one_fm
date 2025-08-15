def get_attendance_request_custom_fields():
    return {
        "Attendance Request": [
            {
                "fieldname": "approver_user",
                "fieldtype": "Link",
                "insert_after": "approver_name",
                "label": "Approver User",
                "options": "User",
                "read_only": 1
            },
            {
                "fieldname": "approver_name",
                "fieldtype": "Data",
                "insert_after": "approver",
                "label": "Approver Name",
                "read_only": 1
            },
            {
                "fieldname": "approver",
                "fieldtype": "Link",
                "insert_after": "update_request",
                "label": "Approver",
                "options": "Employee",
                "read_only": 1
            },
            {
                "fieldname": "update_request",
                "fieldtype": "Check",
                "insert_after": "department",
                "label": "Update Request",
                "depends_on": "eval: doc.docstatus > 0",
                "read_only": 1
            }
        ]
    }
