def get_job_applicant_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "applicant_name",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "applicant_rating",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "designation",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "job_title.designation"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "job_title",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"interview_rounds_sb\", \"interview_rounds\", \"details_section\", \"applicant_name\", \"email_id\", \"one_fm_application_id\", \"phone_number\", \"country\", \"column_break_3\", \"job_title\", \"one_fm_designation\", \"applicant_lead\", \"designation\", \"status\", \"one_fm_reason_for_rejection\", \"one_fm_applicant_status\", \"mark_as_shortlisted_first\", \"one_fm_document_verification\", \"source_and_rating_section\", \"source\", \"source_name\", \"one_fm_erf_application_details_section\", \"one_fm_erf\", \"project\", \"department\", \"one_fm_sourcing_team\", \"one_fm_agency\", \"one_fm_is_agency_applying\", \"one_fm_job_applicant_cb_1\", \"one_fm_source_of_hire\", \"one_fm_hiring_method\", \"interview_round\", \"bulk_interview\", \"employment_type\", \"attendance_by_timesheet\", \"one_fm_applicant_personal_details_sb\", \"one_fm_first_name\", \"one_fm_second_name\", \"one_fm_third_name\", \"one_fm_forth_name\", \"one_fm_last_name\", \"one_fm_first_name_in_arabic\", \"one_fm_second_name_in_arabic\", \"one_fm_third_name_in_arabic\", \"one_fm_forth_name_in_arabic\", \"one_fm_last_name_in_arabic\", \"one_fm_height\", \"one_fm_i_am_currently_working\", \"one_fm_applicant_demographics_cb\", \"one_fm_gender\", \"one_fm_religion\", \"one_fm_date_of_birth\", \"one_fm_place_of_birth\", \"one_fm_marital_status\", \"one_fm_nationality\", \"one_fm_date_of_entry\", \"employee_referral\", \"column_break_13\", \"applicant_rating\", \"section_break_6\", \"notes\", \"cover_letter\", \"resume_attachment\", \"children_details_section\", \"one_fm_number_of_kids\", \"one_fm_kids_details\", \"day_off_details\", \"day_off_category\", \"column_break_66\", \"number_of_days_off\", \"one_fm_work_details_section\", \"one_fm_rotation_shift\", \"one_fm_night_shift\", \"one_fm_work_details_cb\", \"one_fm_type_of_travel\", \"one_fm_type_of_driving_license\", \"one_fm_uniform_measurements\", \"one_fm_is_uniform_needed_for_this_job\", \"one_fm_shoulder_width\", \"one_fm_waist_size\", \"one_fm_shoe_size\", \"one_fm_basic_skill_section\", \"one_fm_designation_skill\", \"one_fm_documents_required_section\", \"one_fm_documents_required\", \"one_fm_is_easy_apply\", \"previous_work_details\", \"one_fm_work_permit_number\", \"one_fm_duration_of_work_permit\", \"one_fm_previous_designation\", \"column_break_51\", \"one_fm_work_permit_salary\", \"one_fm_last_working_date\", \"resume_link\", \"section_break_16\", \"currency\", \"column_break_18\", \"lower_range\", \"upper_range\", \"one_fm_contact_details_section\", \"one_fm_email_id\", \"one_fm_country_code\", \"one_fm_contact_number\", \"one_fm_country_code_second\", \"one_fm_secondary_contact_number\", \"one_fm_contact_cb\", \"one_fm_language_section\", \"one_fm_languages\", \"country_and_nationality_section\", \"nationality_no\", \"nationality_subject\", \"nationality_cb\", \"date_of_naturalization\", \"one_fm_passport_section\", \"one_fm_passport_number\", \"one_fm_passport_holder_of\", \"one_fm_passport_issued\", \"one_fm_passport_expire\", \"one_fm_passport_cb\", \"one_fm_passport_type\", \"one_fm_centralized_number\", \"one_fm_visa_and_residency_section\", \"one_fm_have_a_valid_visa_in_kuwait\", \"one_fm_visa_type\", \"one_fm_cid_number\", \"one_fm_cid_expire\", \"one_fm_in_kuwait_at_present\", \"one_fm_visa_cb\", \"one_fm_current_employment_section_\", \"one_fm_current_employer\", \"one_fm_current_employer_website_link\", \"one_fm_employment_start_date\", \"one_fm_employment_end_date\", \"one_fm_current_employment_cb\", \"one_fm_current_job_title\", \"one_fm_current_salary\", \"one_fm_notice_period_in_days\", \"one_fm_educational_qualification_section\", \"one_fm_educational_qualification\", \"other_education\", \"one_fm_education_specialization\", \"one_fm_educational_qualification_cb\", \"one_fm_university\", \"one_fm_country_of_employment\", \"section_break_88\", \"one_fm_are_you_currently_studying\", \"one_fm_current_educational_institution\", \"column_break_91\", \"one_fm_place_of_study\", \"one_fm_entry_date_of_current_educational_institution\", \"section_break_66\", \"one_fm_applicant_is_overseas_or_local\", \"one_fm_country_of_overseas\", \"one_fm_is_transferable\", \"custom_transfer_reminder_date\", \"column_break_72\", \"one_fm_applicant_password\", \"authorized_signatory\", \"one_fm_old_number\", \"one_fm_old_designation\", \"one_fm_erf_pam_file_number\", \"one_fm_erf_pam_designation\", \"send_changes_to_supervisor\", \"accept_changes\", \"reject_changes\", \"suggestions\", \"save_me\", \"no_internal_issues\", \"one_fm_has_issue\", \"one_fm_type_of_issues\", \"column_break_149\", \"one_fm_change_pam_file_number\", \"pam_number_button\", \"pam_designation_button\", \"one_fm_change_pam_designation\", \"column_break_152\", \"one_fm_pam_file_number\", \"one_fm_pam_designation\", \"column_break_154\", \"one_fm_file_number\", \"one_fm_notify_recruiter\", \"previous_company_details\", \"one_fm_previous_company_trade_name_in_arabic\", \"one_fm__previous_company_authorized_signatory_name_arabic\", \"one_fm_previous_company_issuer_number\", \"column_break_142\", \"one_fm_previous_company_pam_file_number\", \"one_fm_government_project\", \"authorized_signatory_section\", \"one_fm_pam_authorized_signatory\", \"one_fm_signatory_name\", \"one_fm_grd_operator\", \"scans\", \"passport_data_page\", \"civil_id_front\", \"civil_id_back\", \"high_school_certificate\", \"magic_link_details\", \"career_history_ml\", \"career_history_ml_url\", \"career_history_ml_expired\", \"column_break_avxor\", \"applicant_doc_ml\", \"applicant_doc_ml_url\", \"applicant_doc_ml_expired\"]"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "one_fm_designation",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "one_fm_erf",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "one_fm_reason_for_rejection",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "phone_number",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "status",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Applicant",
            "doctype_or_field": "DocField",
            "field_name": "status",
            "property": "options",
            "property_type": "Text",
            "value": "Open\nReplied\nRejected\nHold\nAccepted"
        }
    ]
