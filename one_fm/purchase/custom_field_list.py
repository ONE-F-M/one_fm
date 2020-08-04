custom_fields = {
    'Purchase Order':['one_fm_warehouse_contact_person', 'one_fm_contact_person_email', 'one_fm_request_for_purchase',
    	'one_fm_contact_person_phone', 'one_fm_warehouse_location', 'one_fm_details_of_other_documents',
        'one_fm_po_document_section', 'one_fm_certificate_of_origin_required', 'one_fm_other_documents_required',
        'one_fm_type_of_purchase', 'one_fm_po_document_cb'],
    'Purchase Receipt':['one_fm_attach_delivery_note'],
    'Purchase Receipt Item':['one_fm_serial_no_and_batch_section', 'one_fm_serial_numbers', 'one_fm_batch_numbers',
        'one_fm_serial_no_and_batch_cb'],
    'Contact':['one_fm_civil_id', 'one_fm_doc_contact_field'],
    'Payment Entry':['one_fm_mode_of_payment_type'],
    'Payment Schedule':['one_fm_payment'],
    'Payment Terms Template Detail':['one_fm_payment'],
    'Payment Term':['one_fm_payment'],
    'Item':['one_fm_item_description_cb'],
    'Stock Entry Detail':['one_fm_request_for_material', 'one_fm_request_for_material_item'],
    'Stock Entry':['one_fm_request_for_material'],
    'Leave Type':['one_fm_sb_leave_payment_breakdown', 'one_fm_leave_payment_breakdown', 'one_fm_is_paid_sick_leave',
        'one_fm_paid_sick_leave_deduction_salary_component', 'one_fm_is_hajj_leave', 'one_fm_is_paid_annual_leave',
        'one_fm_sb_annual_leave_allocation_reduction', 'one_fm_paid_sick_leave_type_dependent',
        'one_fm_annual_leave_allocation_reduction'],
    'Warehouse':['one_fm_is_project_warehouse', 'one_fm_project', 'one_fm_site', 'one_fm_project_details_section', 'one_fm_location',
        'one_fm_main_warehouse', 'one_fm_project_warehouse_code', 'one_fm_store_keeper', 'one_fm_is_main_warehouse'],
    'Project':['one_fm_project_code'],
    'Designation': ['one_fm_tools_required_section', 'one_fm_tools_required', 'one_fm_languages_section', 'one_fm_languages',
        'one_fm_other_details_section', 'one_fm_is_height_mandatory', 'one_fm_shift_working', 'one_fm_night_shift',
        'one_fm_travel_required', 'one_fm_type_of_travel', 'one_fm_other_details_cb', 'one_fm_driving_license_required',
        'one_fm_type_of_license', 'one_fm_is_uniform_needed_for_this_job', 'one_fm_education_qualification',
        'designation_abbreviation', 'performance_profile_details'],
    'Job Applicant': ['one_fm_reason_for_rejection', 'one_fm_applicant_status']
}

def get_custom_field_name_list(doctype_list):
    custom_field_name_list = []
    for doctype in doctype_list:
        doctype_custom_field_list = custom_fields[doctype]
        for custom_fieldname in doctype_custom_field_list:
            custom_field_name_list.append(doctype+'-'+custom_fieldname)
    return custom_field_name_list
