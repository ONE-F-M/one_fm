def get_job_applicant_custom_fields():
    return {
        "Job Applicant": [
            {
                "fieldname": "application_date",
                "fieldtype": "Datetime",
                "label": "Application Date",
                "insert_after": "country",
                "is_system_generated": 1,
                "read_only": 1
            },
            {
                "fieldname": "accept_changes",
                "fieldtype": "Check",
                "label": "Accept Changes By Supervisor",
                "insert_after": "send_changes_to_supervisor",
                "permlevel": 2,
                "read_only_depends_on": '"GRD Operator" == frappe.session.user'
            },
            {
                "fieldname": "applicant_doc_ml",
                "fieldtype": "Link",
                "label": "Applicant Doc ML",
                "insert_after": "column_break_avxor",
                "options": "Magic Link"
            },
            {
                "fieldname": "applicant_doc_ml_expired",
                "fieldtype": "Check",
                "label": "Applicant Doc ML Expired",
                "insert_after": "applicant_doc_ml_url",
                "fetch_from": "applicant_doc_ml.expired"
            },
            {
                "fieldname": "applicant_doc_ml_url",
                "fieldtype": "Small Text",
                "label": "Applicant Doc ML URL",
                "insert_after": "applicant_doc_ml",
                "translatable": 1
            },
            {
                "fieldname": "applicant_lead",
                "fieldtype": "Link",
                "label": "Applicant Lead",
                "insert_after": "one_fm_designation",
                "options": "Applicant Lead",
                "read_only": 1
            },
            {
                "fieldname": "attendance_by_timesheet",
                "fieldtype": "Check",
                "label": "Attendance by Timesheet",
                "insert_after": "employment_type",
                "fetch_from": "employment_type.attendance_by_timesheet",
                "read_only": 1
            },
            {
                "fieldname": "authorized_signatory",
                "fieldtype": "Section Break",
                "label": "GRD Check",
                "insert_after": "one_fm_applicant_password",
                "permlevel": 1
            },
            {
                "fieldname": "authorized_signatory_section",
                "fieldtype": "Section Break",
                "label": "Authorized Signatory Section",
                "insert_after": "one_fm_government_project",
                "depends_on": "one_fm_has_issue",
                "permlevel": 1
            },
            {
                "fieldname": "bulk_interview",
                "fieldtype": "Link",
                "label": "Bulk Interview",
                "insert_after": "interview_round",
                "options": "Interview",
                "read_only": 1
            },
            {
                "fieldname": "career_history_ml",
                "fieldtype": "Link",
                "label": "Career History ML",
                "insert_after": "magic_link_details",
                "options": "Magic Link"
            },
            {
                "fieldname": "career_history_ml_expired",
                "fieldtype": "Check",
                "label": "Career History ML Expired",
                "insert_after": "career_history_ml_url",
                "fetch_from": "career_history_ml.expired"
            },
            {
                "fieldname": "career_history_ml_url",
                "fieldtype": "Small Text",
                "label": "Career History ML URL",
                "insert_after": "career_history_ml",
                "translatable": 1
            },
            {
                "fieldname": "children_details_section",
                "fieldtype": "Section Break",
                "label": "Children Details Section",
                "insert_after": "resume_attachment",
                "depends_on": 'eval: doc.one_fm_marital_status != "Single" && doc.one_fm_nationality == "Kuwaiti"'
            },
            {
                "fieldname": "civil_id_back",
                "fieldtype": "Attach Image",
                "label": "Civil ID Back",
                "insert_after": "civil_id_front"
            },
            {
                "fieldname": "civil_id_front",
                "fieldtype": "Attach Image",
                "insert_after": "passport_data_page",
                "label": "Civil ID Front"
            },
            {
                "fieldname": "column_break_142",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_previous_company_issuer_number"
            },
            {
                "fieldname": "column_break_149",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_type_of_issues"
            },
            {
                "fieldname": "column_break_152",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_change_pam_designation"
            },
            {
                "fieldname": "column_break_154",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_pam_designation"
            },
            {
                "fieldname": "column_break_51",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_previous_designation"
            },
            {
                "fieldname": "column_break_66",
                "fieldtype": "Column Break",
                "insert_after": "day_off_category"
            },
            {
                "fieldname": "column_break_72",
                "fieldtype": "Column Break",
                "insert_after": "custom_transfer_reminder_date"
            },
            {
                "fieldname": "column_break_91",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_current_educational_institution"
            },
            {
                "fieldname": "column_break_avxor",
                "fieldtype": "Column Break",
                "insert_after": "career_history_ml_expired"
            },
            {
                "fieldname": "country_and_nationality_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_languages",
                "label": "Nationality Details",
                "collapsible": 1,
                "depends_on": "eval:doc.one_fm_nationality=='Kuwaiti'"
            },
            {
                "fieldname": "custom_high_school_certificate",
                "fieldtype": "Attach",
                "insert_after": "civil_id_back",
                "label": "High School Certificate"
            },
            {
                "fieldname": "mark_as_shortlisted_first",
                "fieldtype": "Check",
                "insert_after": "one_fm_applicant_status",
                "label": "Mark as Shortlisted First",
                "hidden": 1
            },
            {
                "fieldname": "custom_transfer_reminder_date",
                "fieldtype": "Date",
                "insert_after": "one_fm_is_transferable",
                "label": "Transfer Reminder Date",
                "depends_on": "eval:doc.one_fm_is_transferable==\"Later\"",
                "mandatory_depends_on": "eval:doc.one_fm_is_transferable==\"Later\""
            },
            {
                "fieldname": "date_of_naturalization",
                "fieldtype": "Date",
                "insert_after": "nationality_cb",
                "label": "Date of Naturalization",
                "depends_on": "eval:doc.one_fm_nationality=='Kuwaiti'"
            },

            {
                "fetch_from": "one_fm_erf.day_off_category",
                "fieldname": "day_off_category",
                "fieldtype": "Select",
                "insert_after": "day_off_details",
                "label": "Day off Category",
                "options": "Weekly\nMonthly",
                "translatable": 1
            },
            {
                "collapsible": 1,
                "fieldname": "day_off_details",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_kids_details",
                "label": "Day Off Details"
            },
            {
                "fetch_from": "one_fm_erf.department",
                "fetch_if_empty": 1,
                "fieldname": "department",
                "fieldtype": "Link",
                "insert_after": "project",
                "label": "Department",
                "options": "Department",
                "read_only": 1
            },
            {
                "fetch_from": "one_fm_erf.employment_type",
                "fetch_if_empty": 1,
                "fieldname": "employment_type",
                "fieldtype": "Link",
                "insert_after": "bulk_interview",
                "label": "Employment Type",
                "options": "Employment Type"
            },
            {
                "depends_on": "eval: doc.one_fm_hiring_method  == 'Bulk Recruitment'",
                "fetch_from": "one_fm_erf.interview_round",
                "fetch_if_empty": 1,
                "fieldname": "interview_round",
                "fieldtype": "Link",
                "insert_after": "one_fm_hiring_method",
                "label": "Interview Round",
                "options": "Interview Round",
                "read_only": 1
            },
            {
                "depends_on": "eval:!doc.is_local && doc.one_fm_erf",
                "fieldname": "interview_rounds",
                "fieldtype": "Table",
                "insert_after": "interview_rounds_sb",
                "label": "Interview Rounds",
                "options": "Job Applicant Interview Round"
            },
            {
                "collapsible": 1,
                "fieldname": "interview_rounds_sb",
                "fieldtype": "Section Break",
                "label": "Interview Rounds"
            },
            {
                "fieldname": "magic_link_details",
                "fieldtype": "Section Break",
                "hidden": 1,
                "insert_after": "custom_high_school_certificate",
                "label": "Magic Link Details"
            },
            {
                "fieldname": "nationality_cb",
                "fieldtype": "Column Break",
                "insert_after": "nationality_subject"
            },
            {
                "depends_on": "eval:doc.one_fm_nationality=='Kuwaiti'",
                "fieldname": "nationality_no",
                "fieldtype": "Data",
                "insert_after": "country_and_nationality_section",
                "label": "Nationality No",
                "translatable": 1
            },
            {
                "depends_on": "eval:doc.one_fm_nationality=='Kuwaiti'",
                "fieldname": "nationality_subject",
                "fieldtype": "Select",
                "insert_after": "nationality_no",
                "label": "Nationality Subject",
                "options": "\nالأولي\nالثانية\nالثالثة\nالرابعة\nالخامسة\nالسابعة\nالثامنة",
                "translatable": 1
            },
            {
                "default": "0",
                "fieldname": "no_internal_issues",
                "fieldtype": "Check",
                "insert_after": "save_me",
                "label": "No Internal Issues",
                "permlevel": 1,
                "read_only_depends_on": '"GRD Supervisor" || "Recruiter" || "Senior Recruiter" == frappe.session.user'
            },
            {
                "fetch_from": "one_fm_erf.number_of_days_off",
                "fetch_if_empty": 1,
                "fieldname": "number_of_days_off",
                "fieldtype": "Int",
                "insert_after": "column_break_66",
                "label": "Number of Days Off"
            },
            {
                "fieldname": "one_fm__previous_company_authorized_signatory_name_arabic",
                "fieldtype": "Data",
                "insert_after": "one_fm_previous_company_trade_name_in_arabic",
                "label": "Authorized Signatory Name Arabic",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "depends_on": "eval:doc.one_fm_sourcing_team == 'Agency' || doc.one_fm_sourcing_team == 'One FM and Agency'",
                "fieldname": "one_fm_agency",
                "fieldtype": "Link",
                "insert_after": "one_fm_sourcing_team",
                "in_standard_filter": 1,
                "label": "Agency",
                "options": "Agency"
            },
            {
                "fieldname": "one_fm_applicant_demographics_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_i_am_currently_working"
            },
            {
                "fieldname": "one_fm_applicant_is_overseas_or_local",
                "fieldtype": "Select",
                "insert_after": "section_break_66",
                "label": "Applicant Is Overseas or Local",
                "options": "\nLocal\nOverseas",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_applicant_password",
                "fieldtype": "Data",
                "insert_after": "column_break_72",
                "label": "Applicant Password",
                "hidden": 1,
                "translatable": 1
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_applicant_personal_details_sb",
                "fieldtype": "Section Break",
                "insert_after": "attendance_by_timesheet",
                "label": "Applicant Personal Details"
            },
            {
                "default": "Draft",
                "fieldname": "one_fm_applicant_status",
                "fieldtype": "Select",
                "insert_after": "one_fm_reason_for_rejection",
                "label": "Applicant Status",
                "in_standard_filter": 1,
                "options": "\nDraft\nApplicant Filtered\nShortlisted\nInterview Scheduled\nInterview\nInterview Completed\nSelected\nChecked By GRD",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_application_id",
                "fieldtype": "Data",
                "insert_after": "email_id",
                "label": "Application ID",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_are_you_currently_studying",
                "fieldtype": "Select",
                "insert_after": "section_break_88",
                "label": "Are You Currently Studying",
                "options": "\nYes\nNo",
                "translatable": 1
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_basic_skill_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_shoe_size",
                "label": "Basic Skill"
            },
            {
                "fieldname": "one_fm_centralized_number",
                "fieldtype": "Data",
                "insert_after": "one_fm_passport_type",
                "label": "Centralized Number",
                "hidden": 1,
                "translatable": 1
            },
            {
                "permlevel": 1,
                "fieldname": "one_fm_change_pam_designation",
                "fieldtype": "Button",
                "insert_after": "pam_designation_button",
                "label": "Change PAM Designation"
            },
            {
                "permlevel": 1,
                "fieldname": "one_fm_change_pam_file_number",
                "fieldtype": "Button",
                "insert_after": "column_break_149",
                "label": "Change PAM File Number"
            },
            {
                "depends_on": "one_fm_have_a_valid_visa_in_kuwait",
                "fieldname": "one_fm_cid_expire",
                "fieldtype": "Date",
                "insert_after": "one_fm_cid_number",
                "label": "Civil ID Valid Till"
            },
            {
                "in_standard_filter": 1,
                "depends_on": "one_fm_have_a_valid_visa_in_kuwait",
                "fieldname": "one_fm_cid_number",
                "fieldtype": "Data",
                "insert_after": "one_fm_visa_type",
                "label": "CIVIL ID",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_contact_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_secondary_contact_number"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_contact_details_section",
                "fieldtype": "Section Break",
                "insert_after": "upper_range",
                "label": "Contact Details",
                "description": "Below mentioned details will be our primary modes of contact. please make sure you mention the correct details here."
            },
            {
                "fieldname": "one_fm_contact_number",
                "fieldtype": "Data",
                "insert_after": "one_fm_country_code",
                "label": "Contact Number",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_country_code",
                "fieldtype": "Link",
                "insert_after": "one_fm_email_id",
                "label": "Country Code for Primary Contact Number",
                "options": "Country Calling Code"
            },
            {
                "fieldname": "one_fm_country_code_second",
                "fieldtype": "Link",
                "insert_after": "one_fm_contact_number",
                "label": "Country Code for Emergency Contact Number",
                "options": "Country Calling Code"
            },
            {
                "fieldname": "one_fm_country_of_employment",
                "fieldtype": "Link",
                "insert_after": "one_fm_university",
                "label": "Country of Employment",
                "options": "Country"
            },
            {
                "depends_on": "eval:doc.one_fm_applicant_is_overseas_or_local == 'Overseas'",
                "fieldname": "one_fm_country_of_overseas",
                "fieldtype": "Link",
                "insert_after": "one_fm_applicant_is_overseas_or_local",
                "label": "Country",
                "options": "Country"
            },
            {
                "fieldname": "one_fm_current_educational_institution",
                "fieldtype": "Data",
                "insert_after": "one_fm_are_you_currently_studying",
                "label": "Current Educational Institution",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_current_employer",
                "fieldtype": "Data",
                "insert_after": "one_fm_current_employment_section_",
                "label": "Current Employer",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_current_employer_website_link",
                "fieldtype": "Data",
                "insert_after": "one_fm_current_employer",
                "label": "Current Employer Website Link",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_current_employment_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_employment_end_date"
            },
            {
                "collapsible": 1,
                "depends_on": "one_fm_i_am_currently_working",
                "fieldname": "one_fm_current_employment_section_",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_visa_cb",
                "label": "Current Employment "
            },
            {
                "fieldname": "one_fm_current_job_title",
                "fieldtype": "Data",
                "insert_after": "one_fm_current_employment_cb",
                "label": "Current Job Title",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_current_salary",
                "fieldtype": "Currency",
                "insert_after": "one_fm_current_job_title",
                "label": "Current Monthly Salary in KWD"
            },
            {
                "fieldname": "one_fm_date_of_birth",
                "fieldtype": "Date",
                "insert_after": "one_fm_religion",
                "label": "Date of Birth",
                "description": "Date of Birth on the Passport"
            },
            {
                "fieldname": "one_fm_date_of_entry",
                "fieldtype": "Date",
                "insert_after": "one_fm_nationality",
                "label": "Date of Entry",
                "hidden": 1
            },
            {
                "fetch_from": "job_title.designation",
                "fieldname": "one_fm_designation",
                "fieldtype": "Link",
                "insert_after": "job_title",
                "label": "Applied Designation",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "options": "Designation",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_designation_skill",
                "fieldtype": "Table",
                "insert_after": "one_fm_basic_skill_section",
                "label": "Skills",
                "options": "Designation Skill"
            },
            {
                "fieldname": "one_fm_document_verification",
                "fieldtype": "Select",
                "insert_after": "mark_as_shortlisted_first",
                "label": "Document Verification",
                "options": "\nNot Applicable\nNot Verified\nVerified\nVerified - With Exception",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_documents_required",
                "fieldtype": "Table",
                "insert_after": "one_fm_documents_required_section",
                "options": "Job Applicant Required Document"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_documents_required_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_designation_skill",
                "label": "Documents Required"
            },
            {
                "fieldname": "one_fm_duration_of_work_permit",
                "fieldtype": "Float",
                "insert_after": "one_fm_work_permit_number",
                "label": "Duration of Work Permit"
            },
            {
                "fieldname": "one_fm_education_specialization",
                "fieldtype": "Data",
                "insert_after": "other_education",
                "label": "Specialization",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_educational_qualification",
                "fieldtype": "Select",
                "insert_after": "one_fm_educational_qualification_section",
                "label": "What is Your Highest Educational Qualification",
                "options": "\nN/A\nPrimary\nMiddle School\nHigh School\nUnder Graduate\nDiploma\nBachelor\nMasters\nPhD\nOthers",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_educational_qualification_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_education_specialization"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_educational_qualification_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_notice_period_in_days",
                "label": "Educational Qualification"
            },
            {
                "fieldname": "one_fm_email_id",
                "fieldtype": "Data",
                "insert_after": "one_fm_contact_details_section",
                "label": "Email ID",
                "description": "You will be getting updates on the candidature on the mentioned email.",
                "options": "Email",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_employment_end_date",
                "fieldtype": "Date",
                "insert_after": "one_fm_employment_start_date",
                "label": "Employment End Date"
            },
            {
                "fieldname": "one_fm_employment_start_date",
                "fieldtype": "Date",
                "insert_after": "one_fm_current_employer_website_link",
                "label": "Employment Start Date"
            },
            {
                "fieldname": "one_fm_entry_date_of_current_educational_institution",
                "fieldtype": "Date",
                "insert_after": "one_fm_place_of_study",
                "label": "Entry Date of Current Educational Institution"
            },
            {
                "fieldname": "one_fm_erf",
                "fieldtype": "Link",
                "insert_after": "one_fm_erf_application_details_section",
                "label": "ERF",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "options": "ERF"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_erf_application_details_section",
                "fieldtype": "Section Break",
                "insert_after": "source_name"
            },
            {
                "fieldname": "one_fm_designation_skill",
                "fieldtype": "Table",
                "insert_after": "one_fm_basic_skill_section",
                "label": "Skills",
                "options": "Designation Skill"
            },
            {
                "fieldname": "one_fm_document_verification",
                "fieldtype": "Select",
                "insert_after": "mark_as_shortlisted_first",
                "label": "Document Verification",
                "options": "\nNot Applicable\nNot Verified\nVerified\nVerified - With Exception",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_documents_required",
                "fieldtype": "Table",
                "insert_after": "one_fm_documents_required_section",
                "options": "Job Applicant Required Document"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_documents_required_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_designation_skill",
                "label": "Documents Required"
            },
            {
                "fieldname": "one_fm_duration_of_work_permit",
                "fieldtype": "Float",
                "insert_after": "one_fm_work_permit_number",
                "label": "Duration of Work Permit"
            },
            {
                "fieldname": "one_fm_education_specialization",
                "fieldtype": "Data",
                "insert_after": "other_education",
                "label": "Specialization",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_educational_qualification",
                "fieldtype": "Select",
                "insert_after": "one_fm_educational_qualification_section",
                "label": "What is Your Highest Educational Qualification",
                "options": "\nN/A\nPrimary\nMiddle School\nHigh School\nUnder Graduate\nDiploma\nBachelor\nMasters\nPhD\nOthers",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_educational_qualification_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_education_specialization"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_educational_qualification_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_notice_period_in_days",
                "label": "Educational Qualification"
            },
            {
                "fieldname": "one_fm_email_id",
                "fieldtype": "Data",
                "insert_after": "one_fm_contact_details_section",
                "label": "Email ID",
                "description": "You will be getting updates on the candidature on the mentioned email.",
                "options": "Email",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_employment_end_date",
                "fieldtype": "Date",
                "insert_after": "one_fm_employment_start_date",
                "label": "Employment End Date"
            },
            {
                "fieldname": "one_fm_employment_start_date",
                "fieldtype": "Date",
                "insert_after": "one_fm_current_employer_website_link",
                "label": "Employment Start Date"
            },
            {
                "fieldname": "one_fm_entry_date_of_current_educational_institution",
                "fieldtype": "Date",
                "insert_after": "one_fm_place_of_study",
                "label": "Entry Date of Current Educational Institution"
            },
            {
                "fieldname": "one_fm_erf",
                "fieldtype": "Link",
                "insert_after": "one_fm_erf_application_details_section",
                "label": "ERF",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "options": "ERF"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_erf_application_details_section",
                "fieldtype": "Section Break",
                "insert_after": "source_name"
            },
            {
                "depends_on": "eval:doc.one_fm_is_transferable == 'Yes'",
                "fieldname": "one_fm_erf_pam_designation",
                "fieldtype": "Data",
                "insert_after": "one_fm_erf_pam_file_number",
                "label": "PAM Designation",
                "permlevel": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "depends_on": "eval:doc.one_fm_is_transferable == 'Yes'",
                "fetch_from": "\n",
                "fieldname": "one_fm_erf_pam_file_number",
                "fieldtype": "Data",
                "insert_after": "one_fm_old_designation",
                "label": "PAM File Number",
                "permlevel": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fetch_from": "one_fm_pam_file_number.pam_file_number",
                "fieldname": "one_fm_file_number",
                "fieldtype": "Data",
                "insert_after": "column_break_154",
                "label": "File Number",
                "permlevel": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "depends_on": "",
                "fieldname": "one_fm_first_name",
                "fieldtype": "Data",
                "insert_after": "one_fm_applicant_personal_details_sb",
                "label": "First Name",
                "reqd": 1,
                "translatable": 1
            },
            {
                "depends_on": "one_fm_first_name",
                "fieldname": "one_fm_first_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "one_fm_last_name",
                "label": "First Name in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_forth_name",
                "fieldtype": "Data",
                "insert_after": "one_fm_third_name",
                "label": "Forth Name",
                "translatable": 1
            },
            {
                "depends_on": "one_fm_forth_name",
                "fieldname": "one_fm_forth_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "one_fm_third_name_in_arabic",
                "label": "Forth Name in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_gender",
                "fieldtype": "Link",
                "insert_after": "one_fm_applicant_demographics_cb",
                "label": "Gender",
                "options": "Gender"
            },
            {
                "fieldname": "one_fm_government_project",
                "fieldtype": "Check",
                "insert_after": "one_fm_previous_company_pam_file_number",
                "label": "Government Project",
                "permlevel": 1
            },
            {
                "fieldname": "one_fm_grd_operator",
                "fieldtype": "Link",
                "hidden": 1,
                "insert_after": "one_fm_signatory_name",
                "label": "GRD Operator",
                "options": "User"
            },
            {
                "depends_on": "eval: doc.no_internal_issues == 1",
                "fieldname": "one_fm_has_issue",
                "fieldtype": "Select",
                "insert_after": "no_internal_issues",
                "label": "Has Issue",
                "options": "\nYes\nNo",
                "permlevel": 1,
                "translatable": 1,
                "width": "55"
            },
            {
                "fieldname": "one_fm_have_a_valid_visa_in_kuwait",
                "fieldtype": "Check",
                "insert_after": "one_fm_visa_and_residency_section",
                "label": "I Have a Valid Visa in Kuwait"
            },
            {
                "fieldname": "one_fm_height",
                "fieldtype": "Float",
                "insert_after": "one_fm_last_name_in_arabic",
                "label": "Height in cm"
            },
            {
                "fetch_from": "one_fm_erf.hiring_method",
                "fetch_if_empty": 1,
                "fieldname": "one_fm_hiring_method",
                "fieldtype": "Select",
                "insert_after": "one_fm_source_of_hire",
                "label": "Hiring Method",
                "options": "\nBulk Recruitment\nA la carte Recruitment",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_i_am_currently_working",
                "fieldtype": "Check",
                "insert_after": "one_fm_height",
                "label": "Do You Have Previous Work Experience"
            },
            {
                "depends_on": "one_fm_have_a_valid_visa_in_kuwait",
                "fieldname": "one_fm_in_kuwait_at_present",
                "fieldtype": "Check",
                "insert_after": "one_fm_cid_expire",
                "label": "Are You In Kuwait at Present"
            },
            {
                "depends_on": "one_fm_agency",
                "fieldname": "one_fm_is_agency_applying",
                "fieldtype": "Check",
                "insert_after": "one_fm_agency",
                "label": "Is Agency Applying"
            },
            {
                "hidden": 1,
                "fieldname": "one_fm_is_easy_apply",
                "fieldtype": "Check",
                "insert_after": "one_fm_documents_required",
                "label": "Is Easy Apply"
            },
            {
                "depends_on": "eval:doc.one_fm_applicant_is_overseas_or_local == 'Local'",
                "fieldname": "one_fm_is_transferable",
                "fieldtype": "Select",
                "insert_after": "one_fm_country_of_overseas",
                "label": "Do You want to Transfer?",
                "options": "\nYes\nNo\nLater",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_is_uniform_needed_for_this_job",
                "fieldtype": "Check",
                "insert_after": "one_fm_uniform_measurements",
                "label": "Is Uniform Needed for This Job"
            },
            {
                "depends_on": "",
                "fieldname": "one_fm_job_applicant_cb_1",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_is_agency_applying"
            },
            {
                "fieldname": "one_fm_kids_details",
                "fieldtype": "Table",
                "insert_after": "one_fm_number_of_kids",
                "label": "Children Details",
                "mandatory_depends_on": "eval:doc.one_fm_number_of_kids >0",
                "options": "Children Details Table"
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_language_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_contact_cb",
                "label": "Language"
            },
            {
                "fieldname": "one_fm_languages",
                "fieldtype": "Table",
                "insert_after": "one_fm_language_section",
                "options": "Employee Language Requirement"
            },
            {
                "fieldname": "one_fm_last_name",
                "fieldtype": "Data",
                "insert_after": "one_fm_forth_name",
                "label": "Last Name",
                "reqd": 1,
                "translatable": 1
            },
            {
                "depends_on": "one_fm_last_name",
                "fieldname": "one_fm_last_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "one_fm_forth_name_in_arabic",
                "label": "Last Name in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_last_working_date",
                "fieldtype": "Date",
                "insert_after": "one_fm_work_permit_salary",
                "label": "Last Working Date"
            },
            {
                "fieldname": "one_fm_marital_status",
                "fieldtype": "Select",
                "insert_after": "one_fm_place_of_birth",
                "label": "Marital Status",
                "options": "\nUnmarried\nMarried\nDivorce\nWidow\nUnknown",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_nationality",
                "fieldtype": "Link",
                "insert_after": "one_fm_marital_status",
                "label": "Nationality",
                "options": "Nationality"
            },
            {
                "fieldname": "one_fm_night_shift",
                "fieldtype": "Select",
                "insert_after": "one_fm_rotation_shift",
                "label": "Night Shift",
                "options": "\nYes, I Will Work in Night Shift\nNo, I Cant Work in Night Shift",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_notice_period_in_days",
                "fieldtype": "Int",
                "insert_after": "one_fm_current_salary",
                "label": "Notice Period in Days"
            },
            {
                "depends_on": "",
                "hidden": 1,
                "fieldname": "one_fm_notify_recruiter",
                "fieldtype": "Check",
                "insert_after": "one_fm_file_number",
                "label": "Notify Recruiter"
            },
            {
                "fieldname": "one_fm_number_of_kids",
                "fieldtype": "Int",
                "insert_after": "children_details_section",
                "label": "Number of Kids",
                "mandatory_depends_on": "eval: doc.one_fm_marital_status != \"Single\" && doc.one_fm_nationality == \"Kuwaiti\""
            },
            {
                "hidden": 1,
                "fieldname": "one_fm_old_designation",
                "fieldtype": "Data",
                "insert_after": "one_fm_old_number",
                "label": "Old Designation",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "hidden": 1,
                "fieldname": "one_fm_old_number",
                "fieldtype": "Data",
                "insert_after": "authorized_signatory",
                "label": "Old Number",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "allow_on_submit": 1,
                "hidden": 1,
                "fieldname": "one_fm_pam_authorized_signatory",
                "fieldtype": "Data",
                "insert_after": "authorized_signatory_section",
                "label": "PAM Authorized Signatory",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "depends_on": "eval:doc.pam_designation_button == 1",
                "fieldname": "one_fm_pam_designation",
                "fieldtype": "Link",
                "insert_after": "one_fm_pam_file_number",
                "label": "PAM Designation",
                "options": "PAM Designation List",
                "permlevel": 1
            },
            {
                "depends_on": "eval:doc.pam_number_button == 1",
                "fieldname": "one_fm_pam_file_number",
                "fieldtype": "Link",
                "insert_after": "column_break_152",
                "label": "PAM File",
                "options": "PAM File",
                "permlevel": 1
            },
            {
                "depends_on": "",
                "fieldname": "one_fm_passport_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_passport_expire"
            },
            {
                "fieldname": "one_fm_passport_expire",
                "fieldtype": "Date",
                "insert_after": "one_fm_passport_issued",
                "label": "Passport Expires on"
            },
            {
                "fieldname": "one_fm_passport_holder_of",
                "fieldtype": "Link",
                "insert_after": "one_fm_passport_number",
                "label": "Passport Holder of",
                "options": "Country"
            },
            {
                "fieldname": "one_fm_passport_issued",
                "fieldtype": "Date",
                "insert_after": "one_fm_passport_holder_of",
                "label": "Passport Issued on"
            },
            {
                "fieldname": "one_fm_passport_number",
                "fieldtype": "Data",
                "insert_after": "one_fm_passport_section",
                "label": "Passport Number",
                "translatable": 1
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_passport_section",
                "fieldtype": "Section Break",
                "insert_after": "date_of_naturalization",
                "label": "Passport"
            },
            {
                "default": "Normal",
                "fieldname": "one_fm_passport_type",
                "fieldtype": "Select",
                "insert_after": "one_fm_passport_cb",
                "label": "Passport Type",
                "options": "\nDiplomat\nNormal",
                "reqd": 1,
                "translatable": 1
            },
            {
                "description": "Place of Birth on the Passport",
                "fieldname": "one_fm_place_of_birth",
                "fieldtype": "Link",
                "insert_after": "one_fm_date_of_birth",
                "label": "Place of Birth",
                "options": "Country",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_place_of_study",
                "fieldtype": "Select",
                "insert_after": "column_break_91",
                "label": "Place Of Study",
                "options": "\nInside Kuwait\nOutside Kuwait",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_previous_company_issuer_number",
                "fieldtype": "Data",
                "insert_after": "one_fm__previous_company_authorized_signatory_name_arabic",
                "label": "Company license Number",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "fetch_from": "",
                "fieldname": "one_fm_previous_company_pam_file_number",
                "fieldtype": "Data",
                "insert_after": "column_break_142",
                "label": "PAM File Number",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_previous_company_trade_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "previous_company_details",
                "label": "Trade Name in Arabic",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_previous_designation",
                "fieldtype": "Data",
                "insert_after": "one_fm_duration_of_work_permit",
                "label": "Previous Designation",
                "translatable": 1
            },
            {
                "depends_on": "eval:doc.status == 'Rejected'",
                "fieldname": "one_fm_reason_for_rejection",
                "fieldtype": "Small Text",
                "insert_after": "status",
                "label": "Reason for Rejection",
                "in_list_view": 1,
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_religion",
                "fieldtype": "Link",
                "insert_after": "one_fm_gender",
                "label": "Religion",
                "options": "Religion"
            },
            {
                "fieldname": "one_fm_rotation_shift",
                "fieldtype": "Select",
                "insert_after": "one_fm_work_details_section",
                "label": "Rotation Shift",
                "options": "\nYes, I Will Work in Rotation Shift\nNo, I Cant Work in Rotation Shift",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_second_name",
                "fieldtype": "Data",
                "insert_after": "one_fm_first_name",
                "label": "Second Name",
                "translatable": 1
            },
            {
                "depends_on": "one_fm_second_name",
                "fieldname": "one_fm_second_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "one_fm_first_name_in_arabic",
                "label": "Second Name in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_secondary_contact_number",
                "fieldtype": "Data",
                "insert_after": "one_fm_country_code_second",
                "label": "Emergency Contact Number",
                "translatable": 1
            },
            {
                "depends_on": "one_fm_is_uniform_needed_for_this_job",
                "fieldname": "one_fm_shoe_size",
                "fieldtype": "Float",
                "insert_after": "one_fm_waist_size",
                "label": "Shoe Size in Centi Meter"
            },
            {
                "depends_on": "one_fm_is_uniform_needed_for_this_job",
                "fieldname": "one_fm_shoulder_width",
                "fieldtype": "Float",
                "insert_after": "one_fm_is_uniform_needed_for_this_job",
                "label": "Shoulder Width in Centi Meter"
            },
            {
                "fieldname": "one_fm_signatory_name",
                "fieldtype": "Select",
                "insert_after": "one_fm_pam_authorized_signatory",
                "label": "Signatory Name",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_source_of_hire",
                "fieldtype": "Select",
                "insert_after": "one_fm_job_applicant_cb_1",
                "label": "Source of Hire",
                "options": "\nLocal\nOverseas\nLocal and Overseas",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_sourcing_team",
                "fieldtype": "Select",
                "insert_after": "department",
                "label": "Sourcing Team",
                "options": "\nOne FM\nAgency\nOne FM and Agency",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_third_name",
                "fieldtype": "Data",
                "insert_after": "one_fm_second_name",
                "label": "Third Name",
                "translatable": 1
            },
            {
                "depends_on": "one_fm_third_name",
                "fieldname": "one_fm_third_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "one_fm_second_name_in_arabic",
                "label": "Third Name in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_type_of_driving_license",
                "fieldtype": "Select",
                "insert_after": "one_fm_type_of_travel",
                "label": "Type of Driving License",
                "options": "\nLight\nHeavy\nMotor Bike\nInshaya\nNot Available",
                "translatable": 1
            },
            {
                "depends_on": "eval:doc.one_fm_has_issue == \"Yes\"",
                "fieldname": "one_fm_type_of_issues",
                "fieldtype": "Small Text",
                "insert_after": "one_fm_has_issue",
                "label": "Type of Issues",
                "permlevel": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_type_of_travel",
                "fieldtype": "Select",
                "insert_after": "one_fm_work_details_cb",
                "label": "Type of Travel",
                "translatable": 1
            },
            {
                "collapsible": 1,
                "fieldname": "one_fm_uniform_measurements",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_type_of_driving_license",
                "label": "Uniform Measurements"
            },
            {
                "fieldname": "one_fm_university",
                "fieldtype": "Data",
                "insert_after": "one_fm_educational_qualification_cb",
                "label": "University / School"
            },
            {
                "collapsible": 1,
                "hidden": 1,
                "fieldname": "one_fm_visa_and_residency_section",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_centralized_number",
                "label": "Visa and Residency"
            },
            {
                "depends_on": "",
                "fieldname": "one_fm_visa_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_in_kuwait_at_present"
            },
            {
                "depends_on": "one_fm_have_a_valid_visa_in_kuwait",
                "fieldname": "one_fm_visa_type",
                "fieldtype": "Link",
                "insert_after": "one_fm_have_a_valid_visa_in_kuwait",
                "label": "Visa Type",
                "options": "Visa Type"
            },
            {
                "depends_on": "one_fm_is_uniform_needed_for_this_job",
                "fieldname": "one_fm_waist_size",
                "fieldtype": "Float",
                "insert_after": "one_fm_shoulder_width",
                "label": "Waist Size in Centi Meter"
            },
            {
                "depends_on": "",
                "fieldname": "one_fm_work_details_cb",
                "fieldtype": "Column Break",
                "insert_after": "one_fm_night_shift"
            },
            {
                "collapsible": 1,
                "hidden": 1,
                "fieldname": "one_fm_work_details_section",
                "fieldtype": "Section Break",
                "insert_after": "number_of_days_off",
                "label": "Work Details"
            },
            {
                "fieldname": "one_fm_work_permit_number",
                "fieldtype": "Int",
                "insert_after": "previous_work_details",
                "label": "Work Permit Number",
                "permlevel": 2,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_work_permit_salary",
                "fieldtype": "Currency",
                "insert_after": "column_break_51",
                "label": "Previous Work Permit Salary"
            },
            {
                "depends_on": "eval:doc.one_fm_educational_qualification == 'Others'",
                "fieldname": "other_education",
                "fieldtype": "Data",
                "insert_after": "one_fm_educational_qualification",
                "label": "Other Education",
                "translatable": 1
            },
            {
                "fieldname": "pam_designation_button",
                "fieldtype": "Check",
                "hidden": 1,
                "insert_after": "pam_number_button",
                "label": "PAM Designation Button"
            },
            {
                "fieldname": "pam_number_button",
                "fieldtype": "Check",
                "hidden": 1,
                "insert_after": "one_fm_change_pam_file_number",
                "label": "PAM Number Button"
            },
            {
                "fieldname": "passport_data_page",
                "fieldtype": "Attach Image",
                "insert_after": "scans",
                "label": "Passport Data Page"
            },
            {
                "depends_on": "one_fm_has_issue",
                "fieldname": "previous_company_details",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_notify_recruiter",
                "label": "Previous Company Details",
                "permlevel": 1
            },
            {
                "collapsible": 1,
                "fieldname": "previous_work_details",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_is_easy_apply",
                "label": "Previous Work Permit Details"
            },
            {
                "fetch_from": "one_fm_erf.project",
                "fetch_if_empty": 1,
                "fieldname": "project",
                "fieldtype": "Link",
                "insert_after": "one_fm_erf",
                "label": "Project",
                "options": "Project",
                "read_only": 1
            },
            {
                "fieldname": "reject_changes",
                "fieldtype": "Check",
                "insert_after": "accept_changes",
                "label": "Reject Changes By Supervisor",
                "permlevel": 2,
                "read_only_depends_on": "\"GRD Operator\" == frappe.session.user"
            },
            {
                "fieldname": "save_me",
                "fieldtype": "Button",
                "insert_after": "suggestions",
                "label": "Save and Notify Operator",
                "permlevel": 2
            },
            {
                "fieldname": "scans",
                "fieldtype": "Section Break",
                "hidden": 1,
                "insert_after": "one_fm_grd_operator",
                "label": "Scans"
            },
            {
                "collapsible": 1,
                "fieldname": "section_break_88",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_country_of_employment",
                "label": "Current Education"
            },
            {
                "fieldname": "send_changes_to_supervisor",
                "fieldtype": "Button",
                "depends_on": "eval: doc.pam_number_button == 1 || doc.pam_designation_button == 1",
                "insert_after": "one_fm_erf_pam_designation",
                "label": "Save and Send Changes To Supervisor",
                "permlevel": 1
            },
            {
                "depends_on": "eval: doc.reject_changes == 1",
                "fieldname": "suggestions",
                "fieldtype": "Small Text",
                "insert_after": "reject_changes",
                "label": "Suggestions",
                "permlevel": 2,
                "translatable": 1
            },
            {
                "fieldname": "section_break_66",
                "fieldtype": "Section Break",
                "insert_after": "one_fm_entry_date_of_current_educational_institution",
                "label": "Current Education"
            }
        ]
    }
