def get_job_offer_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"workflow_state\", \"job_applicant\", \"one_fm_erf\", \"applicant_name\", \"agency_country_process\", \"agency\", \"applicant_email\", \"onboarding_officer\", \"day_off_category\", \"number_of_days_off\", \"employment_type\", \"attendance_by_timesheet\", \"shift_working_html\", \"shift_working\", \"operations_shift\", \"default_shift\", \"operations_site\", \"project\", \"reports_to\", \"column_break_3\", \"status\", \"offer_date\", \"one_fm_offer_accepted_date\", \"estimated_date_of_joining\", \"department\", \"designation\", \"company\", \"nationality\", \"one_fm_provide_salary_advance\", \"one_fm_salary_advance_amount\", \"one_fm_salary_advance_paid\", \"one_fm_notified_finance_department\", \"one_fm_notify_finance_department\", \"is_g2g_fees_needed\", \"g2g_fee_amount\", \"is_residency_fine_needed\", \"residency_fine_amount\", \"one_fm_salary_details_section\", \"employee_grade\", \"base\", \"one_fm_salary_structure\", \"one_fm_salary_details\", \"one_fm_job_offer_total_salary\", \"section_break_4\", \"job_offer_term_template\", \"offer_terms\", \"one_fm_provide_accommodation_by_company\", \"one_fm_provide_transportation_by_company\", \"section_break_14\", \"select_terms\", \"terms\", \"printing_details\", \"letter_head\", \"url_qr_code\", \"url_qr_code_image\", \"column_break_16\", \"select_print_heading\", \"amended_from\"]"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "read_only",
            "property_type": "Check",
            "field_name": "job_applicant",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "track_changes",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "read_only",
            "property_type": "Check",
            "field_name": "status",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "fetch_from",
            "property_type": "Small Text",
            "field_name": "letter_head",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "default",
            "property_type": "Text",
            "field_name": "letter_head",
            "value": "ONE FM - Job Offer"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Offer",
            "property": "default_print_format",
            "property_type": "Data",
            "value": "One FM Job Offer"
        }
    ]
