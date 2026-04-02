def get_employee_properties():
	return [
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "current_accommodation_type",
			"property": "depends_on",
			"value": "eval:cur_frm.doc.one_fm_provide_accommodation_by_company == 0",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "current_address",
			"property": "read_only_depends_on",
			"value": "eval:cur_frm.doc.one_fm_provide_accommodation_by_company == 1",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "shift",
			"property": "depends_on",
			"value": "eval:!doc.attendance_by_timesheet",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "status",
			"property": "permlevel",
			"value": "1",
			"property_type": "Int",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "reports_to",
			"property": "mandatory_depends_on",
			"value": "",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "marital_status",
			"property": "options",
			"value": "Unmarried\nMarried\nWidow\nDivorce\nUnknown",
			"property_type": "select",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "middle_name",
			"property": "label",
			"value": "Second Name",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "branch",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "civil_id_expiry_date",
			"property": "label",
			"value": "Civil ID Expiry Date",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "column_break1",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "department",
			"property": "reqd",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "employee_number",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "holiday_list",
			"property": "mandatory_depends_on",
			"value": "eval:doc.shift_working==0 && !doc.attendance_by_timesheet",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocType",
			"field_name": None,
			"property": "search_fields",
			"value": "employee_name, employee_id",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocType",
			"field_name": None,
			"property": "no_copy",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "shift",
			"property": "mandatory_depends_on",
			"value": "eval:!doc.attendance_by_timesheet&&!doc.custom_is_reliever",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "shift",
			"property": "label",
			"value": "Shift Allocation",
			"property_type": "Data",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "naming_series",
			"property": "hidden",
			"value": "0",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "naming_series",
			"property": "options",
			"value": "HR-EMP-",
			"property_type": "Text",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "one_fm__highest_educational_qualification",
			"property": "options",
			"value": "\nN/A\nPrimary\nMiddle School\nHigh School\nUnder Graduate\nDiploma\nBachelor\nMasters\nPhD\nOthers",
			"property_type": "select",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocType",
			"field_name": None,
			"property": "track_changes",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "attendance_device_id",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "payroll_cost_center",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "approvers_section",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "date_of_retirement",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "final_confirmation_date",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "last_name",
			"property": "reqd",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "bank_ac_no",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "bank_name",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "status",
			"property": "options",
			"value": "\nActive\nCourt Case\nAbsconding\nLeft\nVacation\nNot Returned from Leave",
			"property_type": "Text",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "employee_number",
			"property": "reqd",
			"value": "0",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocField",
			"field_name": "naming_series",
			"property": "reqd",
			"value": "1",
			"property_type": "Check",
			"default_value": None
		},
		{
			"doc_type": "Employee",
			"doctype_or_field": "DocType",
			"field_name": None,
			"property": "field_order",
			"value": "[\"workflow_state\", \"basic_details_tab\", \"basic_information\", \"employee\", \"naming_series\", \"first_name\", \"middle_name\", \"one_fm_third_name\", \"one_fm_forth_name\", \"last_name\", \"employee_name\", \"column_break_9\", \"one_fm_first_name_in_arabic\", \"one_fm_second_name_in_arabic\", \"one_fm_third_name_in_arabic\", \"one_fm_forth_name_in_arabic\", \"one_fm_last_name_in_arabic\", \"employee_name_in_arabic\", \"gender\", \"date_of_birth\", \"salutation\", \"column_break1\", \"date_of_joining\", \"image\", \"signature\", \"status\", \"employee_id\", \"is_in_ows\", \"erpnext_user\", \"user_id\", \"create_user\", \"create_user_permission\", \"device_os\", \"fcm_token\", \"company_details_section\", \"company\", \"department\", \"coulumn_break_ar2\", \"department_code\", \"employment_type\", \"employee_number\", \"column_break_25\", \"designation\", \"reports_to\", \"government_relation\", \"government_relations\", \"one_fm_pam_designation\", \"pam_file\", \"pam_file_number\", \"residency_expiry_date\", \"under_company_residency\", \"custom_employee_photo\", \"column_break_72\", \"one_fm_work_permit\", \"work_permit\", \"pam_type\", \"custom_employee_image\", \"work_permit_salary\", \"work_permit_expiry_date\", \"column_break_64\", \"one_fm_civil_id\", \"civil_id_expiry_date\", \"one_fm_centralized_number\", \"custom_civil_id_assurance_level\", \"pifss_id_no\", \"is_in_kuwait\", \"grade\", \"arabic_names\", \"column_break_18\", \"branch\", \"column_break_ar1\", \"employment_details\", \"scheduled_confirmation_date\", \"column_break_32\", \"final_confirmation_date\", \"one_fm_visa_reference_number\", \"one_fm_date_of_issuance_of_visa\", \"one_fm_date_of_entry_in_kuwait\", \"one_fm_duration_of_work_permit\", \"contract_end_date\", \"col_break_22\", \"notice_number_of_days\", \"date_of_retirement\", \"one_fm_accommodation_policy\", \"contact_details\", \"cell_number\", \"column_break_40\", \"personal_email\", \"company_email\", \"column_break4\", \"prefered_contact_email\", \"prefered_email\", \"unsubscribed\", \"address_section\", \"current_address\", \"current_accommodation_type\", \"column_break_46\", \"permanent_address\", \"permanent_accommodation_type\", \"emergency_contact_details\", \"person_to_be_contacted\", \"column_break_55\", \"emergency_phone_number\", \"column_break_19\", \"relation\", \"attendance_and_leave_details\", \"attendance_device_id\", \"annual_leave_balance\", \"went_to_hajj\", \"leave_policy\", \"day_off_category\", \"number_of_days_off\", \"attendance_by_timesheet\", \"auto_attendance\", \"non_kuwaiti_residents\", \"column_break_44\", \"shift_working_html\", \"shift_working\", \"custom_is_reliever\", \"custom_is_weekend_reliever\", \"shift\", \"custom_operations_role_allocation\", \"site\", \"project\", \"default_shift\", \"holiday_list\", \"approvers_section\", \"expense_approver\", \"leave_approver\", \"column_break_45\", \"shift_request_approver\", \"salary_information\", \"ctc\", \"salary_currency\", \"salary_mode\", \"salary_cb\", \"payroll_cost_center\", \"custom_payroll_cycle_start_date\", \"custom_payroll_cycle_end_date\", \"bank_details_section\", \"bank_name\", \"column_break_heye\", \"bank_ac_no\", \"one_fm_salary_type\", \"one_fm_basic_salary\", \"iban\", \"personal_details\", \"one_fm_nationality\", \"one_fm_passport_type\", \"marital_status\", \"family_background\", \"column_break6\", \"blood_group\", \"one_fm_religion\", \"one_fm_place_of_birth\", \"health_details\", \"employee_signature\", \"children_details_section\", \"number_of_children\", \"children_details\", \"nationality_details_section\", \"nationality_no\", \"nationality_subject\", \"nationality_cb\", \"date_of_naturalization\", \"health_insurance_section\", \"health_insurance_provider\", \"health_insurance_no\", \"passport_details_section\", \"passport_number\", \"valid_upto\", \"column_break_73\", \"date_of_issue\", \"place_of_issue\", \"profile_tab\", \"bio\", \"educational_qualification\", \"education\", \"one_fm__highest_educational_qualification\", \"previous_work_experience\", \"external_work_history\", \"history_in_company\", \"internal_work_history\", \"one_fm_employee_asset_details_section\", \"one_fm_employee_asset\", \"one_fm_handover_asset\", \"one_fm_employee_documents_section\", \"one_fm_employee_documents\", \"exit\", \"resignation_letter_date\", \"relieving_date\", \"exit_interview_details\", \"held_on\", \"new_workplace\", \"column_break_99\", \"leave_encashed\", \"encashment_date\", \"feedback_section\", \"reason_for_leaving\", \"column_break_104\", \"feedback\", \"lft\", \"rgt\", \"old_parent\", \"subscription_start_date\", \"subscription_end_date\", \"column_break_77\", \"connections_tab\", \"one_fm_erf\", \"one_fm_provide_accommodation_by_company\", \"checkin_location\", \"custom_enable_face_recognition\", \"registered\", \"enrolled\", \"job_offer_details\", \"job_applicant\", \"job_offer\", \"job_offer_salary_structure\", \"bank_account\", \"column_break_120\"]",
			"property_type": "Data",
			"default_value": None
		}
	]