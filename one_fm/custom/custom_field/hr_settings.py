def get_hr_settings_custom_fields():
    return {
        "HR Settings": [
            {
                "fieldname": "custom_hr_manager",
                "fieldtype": "Link",
                "insert_after": "retirement_age",
                "label": "HR Manager",
                "options": "User",
                "description": "User ID of current HR Manager."
            },
            {
                "fieldname": "attendance_check_action_user",
                "fieldtype": "Link",
                "insert_after": "custom_hr_manager",
                "label": "Attendance Check Action User",
                "options": "User",
                "description": "Default Action Owner. Auto-populated into the 'Assigned To' field of every auto-generated Attendance Check Action."
            },
            {
                "fieldname": "payroll_notifications_email",
                "fieldtype": "Data",
                "insert_after": "unlink_payment_on_cancellation_of_employee_advance",
                "label": "Payroll Notifications Email",
                "description": "All payroll related notifications will be forwarded to this email id.",
                "translatable": 1
            },
            {
                "label": "Annual Leave Threshold",
                "fieldname": "annual_leave_threshold",
                "insert_after": "auto_leave_encashment",
                "fieldtype": "Int",
                "default": "60",
                "description": "The minimum number of annual leave days an employee must accumulate before a leave acknowledgment form is automatically generated."
            },
            {
                "fieldname": "government_relations_tab",
                "fieldtype": "Tab Break",
                "insert_after": "payroll_notifications_email",
                "label": "Government Relations"
            },
            {
                "fieldname": "grd_default_settings_section",
                "fieldtype": "Section Break",
                "insert_after": "government_relations_tab",
                "label": "GRD Default Settings"
            },
            {
                "fieldname": "default_grd_supervisor",
                "fieldtype": "Link",
                "insert_after": "grd_default_settings_section",
                "label": "Default GRD Supervisor",
                "options": "User",
                "reqd": 1
            },
            {
                "fieldname": "default_grd_operator",
                "fieldtype": "Link",
                "insert_after": "default_grd_supervisor",
                "label": "Default GRD Operator (Renewal)",
                "options": "User"
            },
            {
                "fieldname": "column_break_grd_1",
                "fieldtype": "Column Break",
                "insert_after": "default_grd_operator"
            },
            {
                "fieldname": "default_grd_operator_pifss",
                "fieldtype": "Link",
                "insert_after": "column_break_grd_1",
                "label": "Default GRD Operator (PIFSS)",
                "options": "User"
            },
            {
                "fieldname": "default_grd_operator_transfer",
                "fieldtype": "Link",
                "insert_after": "default_grd_operator_pifss",
                "label": "Default GRD Operator (Transfer)",
                "options": "User"
            },
            {
                "fieldname": "default_pam_operator",
                "fieldtype": "Link",
                "insert_after": "default_grd_operator_transfer",
                "label": "Default PAM Operator",
                "options": "User"
            },
            {
                "fieldname": "section_break_grd_2",
                "fieldtype": "Section Break",
                "insert_after": "default_pam_operator"
            },
            {
                "fieldname": "days_before_expiry_to_notify_supervisor",
                "fieldtype": "Int",
                "insert_after": "section_break_grd_2",
                "label": "Days Before Expiry to Notify Supervisor",
                "description": "Specify the number of days in advance the supervisor should be notified before an employee's document expires. A notification will be triggered based on this value."
            },
            {
                "fieldname": "paci_fine_amount_kwd",
                "fieldtype": "Currency",
                "insert_after": "days_before_expiry_to_notify_supervisor",
                "label": "PACI Fine Amount (KWD)",
                "description": "The fixed PACI late fine. Fetched onto a PACI record when the operator marks the fine applicable, so the rate is changed in one place when PACI changes it."
            },
            {
                "fieldname": "renewal_extension_costing_section",
                "fieldtype": "Section Break",
                "insert_after": "paci_fine_amount_kwd",
                "label": "Renewal Extension Costing"
            },
            {
                "fieldname": "renewal_extension_cost",
                "fieldtype": "Table",
                "insert_after": "renewal_extension_costing_section",
                "options": "GRD Renewal Extension Cost"
            },
            {
                "fieldname": "nationality_attestation_rules_section",
                "fieldtype": "Section Break",
                "insert_after": "renewal_extension_cost",
                "label": "Nationality Attestation Rules"
            },
            {
                "fieldname": "nationality_attestation_rules",
                "fieldtype": "Table",
                "insert_after": "nationality_attestation_rules_section",
                "options": "Nationality Attestation Rule",
                "description": "What a Police Clearance Certificate needs for each nationality: whether the embassy attests and at what fee, whether MOFA attests and at what fee, and whether the certificate has to be translated. A nationality with no row here needs none of the three."
            },
            {
                "fieldname": "mofa_fee_kwd",
                "fieldtype": "Currency",
                "insert_after": "nationality_attestation_rules",
                "label": "MOFA Fee (KWD)",
                "description": "The standard MOFA attestation fee, used for any nationality whose row in the table above leaves its own MOFA Fee blank."
            },
            {
                "fieldname": "column_break_grd_fees",
                "fieldtype": "Column Break",
                "insert_after": "mofa_fee_kwd"
            },
            {
                "fieldname": "pcc_translation_fee_kwd",
                "fieldtype": "Currency",
                "insert_after": "column_break_grd_fees",
                "label": "PCC Translation Fee (KWD)",
                "description": "The standard fee for translating a Police Clearance Certificate. Applied to a PCC Attestation whose Type is Translation, and to any nationality whose row in the table above is marked Translation Required."
            },
            {
                "fieldname": "costing_section",
                "fieldtype": "Section Break",
                "insert_after": "pcc_translation_fee_kwd",
                "label": "Costing Settings"
            },
            {
                "fieldname": "inform_the_costing_to",
                "fieldtype": "Data",
                "insert_after": "costing_section",
                "label": "Inform The Costing to",
                "options": "Email",
                "description": "Email ID to get informed the finance team about the costing from preparation."
            },
            {
                "fieldname": "costing_print_format",
                "fieldtype": "Link",
                "insert_after": "inform_the_costing_to",
                "label": "Costing Print Format",
                "options": "Print Format",
                "description": "The print format to attach in the notification to the finance team about the preparation cost. If leave this field blank the will consider Standard print format for attachment."
            },
            {
                "fieldname": "penalty_email_section",
                "fieldtype": "Section Break",
                "insert_after": "costing_print_format",
                "label": "Penalty Report Email"
            },
            {
                "fieldname": "penalty_email_recipients",
                "fieldtype": "Table",
                "insert_after": "penalty_email_section",
                "label": "Penalty Email Recipients",
                "options": "Penalty Email Recipient",
                "description": "Who receives the monthly penalty report. TO rows are addressed directly, CC rows are copied. With no rows here the monthly job sends nothing rather than broadcasting to nobody."
            },
            {
                "fieldname": "helpdesk_email",
                "fieldtype": "Data",
                "options": "Email",
                "insert_after": "sender",
                "label": "Helpdesk Email",
                "description": "Email ID of helpdesk user to send reminders or notifications"
            },
            {
                "fieldname": "onboarding_settings_tab",
                "fieldtype": "Tab Break",
                "insert_after": "penalty_email_recipients",
                "label": "Onboarding Settings"
            },
            {
                "fieldname": "onboarding_workspace",
                "fieldtype": "Link",
                "insert_after": "onboarding_settings_tab",
                "label": "Onboarding Workspace",
                "options": "Workspace",
                "description": "The workspace to set as default for onboarding users. If left blank, the default will be 'Wiki'.",
            },
            {
                "fieldname": "wiki_introduction_doc_link",
                "fieldtype": "Data",
                "insert_after": "onboarding_workspace",
                "label": "Wiki Introduction Doc Link",
                "options": "URL",
                "description": "The google doc link for onboarding wiki introduction document.",
            },
            {
                "fieldname": "wiki_assessment_form_link",
                "fieldtype": "Data",
                "insert_after": "wiki_introduction_doc_link",
                "label": "Wiki Assessment Form Link",
                "options": "URL",
                "description": "The google form link for onboarding wiki assessment form.",
            },
            {
                "fieldname": "employee_status_update_notification_email_section",
                "fieldtype": "Section Break",
                "insert_after": "wiki_assessment_form_link",
                "label": "Employee Status Update Notification Email",
                "collapsible": 1,
            },
            {
                "fieldname": "employee_status_update_notification_members",
                "fieldtype": "Table",
                "insert_after": "employee_status_update_notification_email_section",
                "label": "Notification Members",
                "options": "ALM Notification Member",
            },
            {
                "fieldname": "absence_investigation_section",
                "fieldtype": "Section Break",
                "insert_after": "employee_status_update_notification_members",
                "label": "Absence Investigation",
                "collapsible": 1,
            },
            {
                "fieldname": "default_absence_investigation_hr_officer",
                "fieldtype": "Link",
                "insert_after": "absence_investigation_section",
                "label": "Default Absence Investigation HR Officer",
                "options": "User",
                "description": "Primary recipient of automated absence early-warning alerts (e.g. the 5th consecutive day of unexcused absence, and the 16th non-consecutive day of unexcused absence in the calendar year). Alerts are sent to this user's login email.",
            },
        ]
    }