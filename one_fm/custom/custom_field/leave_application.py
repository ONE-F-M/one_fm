def get_leave_application_custom_fields():
    return {
        "Leave Application": [
            {
                "fieldname": "custom_default_leave_application_operator",
                "fieldtype": "Link",
                "insert_after": "status",
                "label": "Default Leave Application Operator",
                "options": "User",
                "read_only": 1
            },
            {
                "fieldname": "custom_is_paid",
                "fieldtype": "Check",
                "insert_after": "amended_from",
                "label": "Is Paid",
                "print_hide": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_propose_from_date",
                "fieldtype": "Date",
                "insert_after": "column_break1",
                "label": "Proposed From Date",
                "in_list_view": 1,
                "read_only": 1
            },
            {
                "fieldname": "custom_propose_to_date",
                "fieldtype": "Date",
                "insert_after": "custom_propose_from_date",
                "label": "Proposed To Date",
                "in_list_view": 1,
                "read_only": 1
            },
            {
                "fieldname": "custom_reason_for_cancel",
                "fieldtype": "Small Text",
                "insert_after": "total_leave_days",
                "label": "Reason for Cancel",
                "allow_on_submit": 1,
                "depends_on": "eval:doc.status === 'Cancelled'",
                "read_only_depends_on": "eval:doc.status === 'Cancelled'"
            },
            {
                "fieldname": "custom_reassigned_documents",
                "fieldtype": "Table",
                "insert_after": "custom_section_break_neyf8",
                "label": "Reassigned Documents",
                "options": "Reassigned Documents",
                "hidden": 1,
                "read_only": 1
            },
            {
                "fieldname": "custom_reliever_",
                "fieldtype": "Link",
                "insert_after": "color",
                "label": "Reliever ",
                "options": "Employee",
                "ignore_user_permissions": 1
            },
            {
                "fieldname": "custom_reliever_name",
                "fieldtype": "Data",
                "insert_after": "custom_reliever_",
                "label": "Reliever Name",
                "fetch_from": "custom_reliever_.employee_name",
                "read_only": 1,
                "ignore_user_permissions": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_section_break_neyf8",
                "fieldtype": "Section Break",
                "insert_after": "source",
                "label": "Reassigned Documents"
            },
            {
                "fieldname": "custom_total_propose_leave_days",
                "fieldtype": "Float",
                "insert_after": "custom_propose_to_date",
                "label": "Total Proposed Leave Days",
                "in_list_view": 1,
                "read_only": 1
            },
            {
                "fieldname": "is_proof_document_required",
                "fieldtype": "Check",
                "insert_after": "leave_type",
                "label": "Is Proof Document Required",
                "fetch_from": "leave_type.is_proof_document_required",
                "read_only": 1,
                "description": "Is Proof Document Required to Apply Leave"
            },
            {
                "fieldname": "proof_document",
                "fieldtype": "Attach",
                "insert_after": "is_proof_document_required",
                "label": "Proof Document",
                "hidden": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "proof_documents",
                "fieldtype": "Table",
                "insert_after": "proof_document",
                "label": "Proof Documents",
                "options": "Proof Documents",
                "depends_on": "is_proof_document_required"
            },
            {
                "fieldname": "resumption_date",
                "fieldtype": "Date",
                "insert_after": "to_date",
                "label": "Resumption Date",
                "description": "Select the date on which you will resume work",
                "reqd": 1,
                "is_system_generated": 1
            },
            {
                "fieldname": "source",
                "fieldtype": "Data",
                "insert_after": "custom_is_paid",
                "label": "Source",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_leave_extension_request",
                "fieldtype": "Link",
                "insert_after": "source",
                "label": "Leave Extension Request",
                "options": "Leave Extension Request",
                "read_only": 1
            },
            {
                "fieldname": "custom_google_event_id",
                "fieldtype": "Data",
                "insert_after": "custom_leave_extension_request",
                "label": "Google Event ID",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_shift_working",
                "fieldtype": "Check",
                "insert_after": "custom_emergency_contact_number",
                "label": "Shift Working",
                "read_only": 1,
                "fetch_from": "employee.shift_working"
            },
            {
                # Emergency contact number for urgent communication during long
                # leaves. Pre-filled from the employee's own mobile (cell_number)
                # but editable by HR. Shown only for shift working employees on
                # Annual Leave or Leave Without Pay; hidden otherwise.
                "fieldname": "custom_emergency_contact_number",
                "fieldtype": "Data",
                "insert_after": "employee_name",
                "label": "Emergency Contact Number",
                "options": "Phone",
                "fetch_from": "employee.cell_number",
                "fetch_if_empty": 1,
                "depends_on": "eval:doc.custom_shift_working && (doc.leave_type=='Annual Leave' || doc.leave_type=='Leave Without Pay')"
            },
            {
                "fieldname": "custom_in_accommodation",
                "fieldtype": "Check",
                "insert_after": "custom_shift_working",
                "label": "In Accommodation",
                "read_only": 1,
                "fetch_from": "employee.one_fm_provide_accommodation_by_company"
            },
            {
                "fieldname": "custom_accommodation_checked_out",
                "fieldtype": "Check",
                "insert_after": "custom_in_accommodation",
                "label": "Accommodation Checked Out",
                "read_only": 1,
                "hidden": 1,
                "allow_on_submit": 1,
                "description": "Set automatically when an OUT Accommodation Leave Movement is submitted"
            },
            {
                "fieldname": "custom_project_allocation",
                "fieldtype": "Link",
                "insert_after": "department",
                "label": "Project Allocation",
                "options": "Project",
                "read_only": 1,
                "fetch_from": "employee.project"
            },
            {
                "fieldname": "resumption_confirmation_details",
                "fieldtype": "Section Break",
                "insert_after": "source",
                "label": "Resumption Confirmation Details",
                # Shown once the leave is Approved and it is an Annual Leave or
                # Leave Without Pay (the leave types HelpDesk follows up on for resumption).
                "depends_on": "eval:doc.workflow_state=='Approved' && (doc.leave_type=='Annual Leave' || doc.leave_type=='Leave Without Pay')",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_could_the_employee_be_reached",
                "fieldtype": "Select",
                "insert_after": "resumption_confirmation_details",
                "label": "Could the Employee be Reached?",
                "options": "\nYes\nNo",
                "allow_on_submit": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_action",
                "fieldtype": "Select",
                "insert_after": "custom_could_the_employee_be_reached",
                "label": "Action",
                "options": "\nTry Again",
                # Set automatically to "Try Again" when the employee could not be reached.
                "read_only": 1,
                "allow_on_submit": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_reason_employee_not_reached",
                "fieldtype": "Small Text",
                "insert_after": "custom_action",
                "label": "Reason Employee Not Reached",
                "description": "State the specific date and time the employee could not be reached",
                # Mandatory audit trail of the unsuccessful contact attempt before escalating.
                "depends_on": "eval:doc.custom_could_the_employee_be_reached=='No'",
                "mandatory_depends_on": "eval:doc.custom_could_the_employee_be_reached=='No'",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_will_the_employee_return",
                "fieldtype": "Select",
                "insert_after": "custom_reason_employee_not_reached",
                "label": "Will the Employee Return?",
                "options": "\nYes\nNo",
                "allow_on_submit": 1,
                "translatable": 1
            },
            {
                "fieldname": "outcome",
                "fieldtype": "Select",
                "insert_after": "resumption_confirmation_details",
                "label": "Outcome",
                "options": "\nConfirmed\nTry again\nResignation\nExtension Request",
                "allow_on_submit": 1
            },
            {
                "fieldname": "return_ticket_submitted",
                "fieldtype": "Select",
                "insert_after": "outcome",
                "label": "Return Ticket Submitted",
                "options": "\nYes\nNo",
                "allow_on_submit": 1,
                "translatable": 1
            },
            {
                "fieldname": "actual_return_date",
                "fieldtype": "Date",
                "insert_after": "return_ticket_submitted",
                "label": "Actual Return Date",
                "allow_on_submit": 1
            },
            {
                "fieldname": "custom_does_the_employee_need_additional_time_to_resume",
                "fieldtype": "Select",
                "insert_after": "actual_return_date",
                "label": "Does the Employee Need Additional Time to Resume?",
                "options": "\nYes\nNo",
                "allow_on_submit": 1,
                "translatable": 1
            },
            {
                "fieldname": "column_break_resumption_details",
                "fieldtype": "Column Break",
                "insert_after": "actual_return_date"
            },
            {
                "fieldname": "attach_return_ticket",
                "fieldtype": "Attach Image",
                "insert_after": "column_break_resumption_details",
                "label": "Attach Return Ticket",
                "depends_on": "eval:doc.return_ticket_submitted == 'Yes'",
                "allow_on_submit": 1
            },
            {
                "fieldname": "reliever_employee_id",
                "fieldtype": "Data",
                "insert_after": "custom_reliever_name",
                "label": "Reliever ID ",
                "fetch_from": "custom_reliever_.employee_id",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "reliever_user_id",
                "fieldtype": "Link",
                "insert_after": "reliever_employee_id",
                "label": "Reliever User ID",
                "options": "User",
                "fetch_from": "custom_reliever_.user_id",
                "read_only": 1
            }
        ]
    }
