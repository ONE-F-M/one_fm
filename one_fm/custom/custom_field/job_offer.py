def get_job_offer_custom_fields():
    return {
        "Job Offer": [
            {
                "fieldname": "url_qr_code_image",
                "fieldtype": "Image",
                "insert_after": "url_qr_code",
                "label": "URL QR Code Image",
                "options": "url_qr_code",
                "description": "Job Offer URL QR Code"
            },
            {
                "fieldname": "url_qr_code",
                "fieldtype": "Small Text",
                "insert_after": "letter_head",
                "label": "URL QR Code",
                "hidden": 1,
                "print_hide": 1,
                "translatable": 1
            },
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "insert_after": "operations_site",
                "label": "Project Allocation",
                "options": "Project",
                "read_only": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "attendance_by_timesheet",
                "fieldtype": "Check",
                "insert_after": "employment_type",
                "label": "Attendance by Timesheet",
                "read_only": 1
            },
            {
                "fieldname": "employment_type",
                "fieldtype": "Link",
                "insert_after": "number_of_days_off",
                "label": "Employment Type",
                "options": "Employment Type",
                "reqd": 1
            },
            {
                "fieldname": "nationality",
                "fieldtype": "Link",
                "insert_after": "company",
                "label": "Nationality",
                "options": "Nationality"
            },
            {
                "fieldname": "department",
                "fieldtype": "Link",
                "insert_after": "estimated_date_of_joining",
                "label": "Department",
                "options": "Department"
            },
            {
                "fieldname": "default_shift",
                "fieldtype": "Link",
                "insert_after": "operations_shift",
                "label": "Default Shift",
                "options": "Shift Type",
                "depends_on": "eval:!doc.attendance_by_timesheet",
                "read_only": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "shift_working",
                "fieldtype": "Check",
                "insert_after": "shift_working_html",
                "label": "Shift Working",
                "hidden": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "shift_working_html",
                "fieldtype": "HTML",
                "insert_after": "attendance_by_timesheet",
                "label": "Shift Working Html",
                "depends_on": "eval:!doc.attendance_by_timesheet"
            },
            {
                "fieldname": "number_of_days_off",
                "fieldtype": "Int",
                "insert_after": "day_off_category",
                "label": "Number of Days Off",
                "reqd": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "day_off_category",
                "fieldtype": "Select",
                "insert_after": "onboarding_officer",
                "label": "Day Off Category",
                "options": "Weekly\nMonthly",
                "reqd": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "base",
                "fieldtype": "Currency",
                "insert_after": "employee_grade",
                "label": "Base"
            },
            {
                "fieldname": "residency_fine_amount",
                "fieldtype": "Currency",
                "insert_after": "is_residency_fine_needed",
                "label": "Residency Fine Amount",
                "depends_on": "is_residency_fine_needed",
                "allow_on_submit": 1
            },
            {
                "fieldname": "is_residency_fine_needed",
                "fieldtype": "Check",
                "insert_after": "g2g_fee_amount",
                "label": "Residency Fine Needed",
                "allow_on_submit": 1
            },
            {
                "fieldname": "g2g_fee_amount",
                "fieldtype": "Currency",
                "insert_after": "is_g2g_fees_needed",
                "label": "G2G Fee Amount",
                "depends_on": "is_g2g_fees_needed",
                "allow_on_submit": 1
            },
            {
                "fieldname": "is_g2g_fees_needed",
                "fieldtype": "Check",
                "insert_after": "one_fm_notify_finance_department",
                "label": "G2G Fees Needed",
                "allow_on_submit": 1
            },
            {
                "fieldname": "operations_site",
                "fieldtype": "Link",
                "insert_after": "default_shift",
                "label": "Site Allocation",
                "options": "Operations Site",
                "depends_on": "eval:doc.shift_working==1 && !doc.attendance_by_timesheet",
                "read_only": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "operations_shift",
                "fieldtype": "Link",
                "insert_after": "shift_working",
                "label": "Shift Allocation",
                "options": "Operations Shift",
                "depends_on": "eval:!doc.attendance_by_timesheet",
                "read_only": 0,
                "allow_on_submit": 1
            },
            {
                "fieldname": "reports_to",
                "fieldtype": "Link",
                "insert_after": "project",
                "label": "Reports To",
                "options": "Employee",
                "read_only": 0,
                "allow_on_submit": 1
            },
            {
                "fieldname": "onboarding_officer",
                "fieldtype": "Link",
                "insert_after": "applicant_email",
                "label": "Onboarding Officer",
                "options": "User",
                "depends_on": "eval:doc.docstatus == 1",
                "allow_on_submit": 1
            },
            {
                "fieldname": "estimated_date_of_joining",
                "fieldtype": "Date",
                "insert_after": "one_fm_offer_accepted_date",
                "label": "Estimated Date of Joining"
            },
            {
                "fieldname": "one_fm_provide_transportation_by_company",
                "fieldtype": "Check",
                "insert_after": "one_fm_provide_accommodation_by_company",
                "label": "Provide Transportation by Company"
            },
            {
                "fieldname": "employee_grade",
                "fieldtype": "Link",
                "insert_after": "one_fm_salary_details_section",
                "label": "Employee Grade",
                "options": "Employee Grade"
            },
            {
                "fieldname": "one_fm_salary_structure",
                "fieldtype": "Link",
                "insert_after": "base",
                "label": "Salary Structure",
                "options": "Salary Structure"
            },
            {
                "fieldname": "one_fm_provide_accommodation_by_company",
                "fieldtype": "Check",
                "insert_after": "offer_terms",
                "label": "Provide Accommodation by Company"
            },
            {
                "fieldname": "one_fm_notify_finance_department",
                "fieldtype": "Button",
                "insert_after": "one_fm_notified_finance_department",
                "label": "Notify Finance Department",
                "depends_on": "eval:doc.one_fm_provide_salary_advance==1 && doc.one_fm_salary_advance_amount > 0 && doc.one_fm_notified_finance_department != 1"
            },
            {
                "fieldname": "one_fm_notified_finance_department",
                "fieldtype": "Check",
                "insert_after": "one_fm_salary_advance_paid",
                "label": "Notified Finance Department",
                "hidden": 1
            },
            {
                "fieldname": "one_fm_salary_advance_paid",
                "fieldtype": "Check",
                "insert_after": "one_fm_salary_advance_amount",
                "label": "Salary Advance Paid",
                "hidden": 1
            },
            {
                "fieldname": "one_fm_salary_advance_amount",
                "fieldtype": "Currency",
                "insert_after": "one_fm_provide_salary_advance",
                "label": "Salary Advance Amount",
                "default": "30",
                "depends_on": "one_fm_provide_salary_advance"
            },
            {
                "fieldname": "one_fm_provide_salary_advance",
                "fieldtype": "Check",
                "insert_after": "nationality",
                "label": "Provide Salary Advance"
            },
            {
                "fieldname": "one_fm_offer_accepted_date",
                "fieldtype": "Date",
                "insert_after": "offer_date",
                "label": "Offer Accepted Date",
                "depends_on": "eval:doc.status=='Accepted'",
                "read_only": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "agency_country_process",
                "fieldtype": "Link",
                "insert_after": "applicant_name",
                "label": "Agency Country Process",
                "options": "Agency Country Process"
            },
            {
                "fieldname": "agency",
                "fieldtype": "Link",
                "insert_after": "agency_country_process",
                "label": "Agency",
                "options": "Agency",
                "fetch_from": "job_applicant.one_fm_agency",
                "fetch_if_empty": 1
            },
            {
                "fieldname": "one_fm_erf",
                "fieldtype": "Link",
                "insert_after": "job_applicant",
                "label": "ERF",
                "options": "ERF",
                "in_standard_filter": 1,
                "read_only": 1,
                "fetch_if_empty": 1
            },
            {
                "fieldname": "one_fm_job_offer_total_salary",
                "fieldtype": "Currency",
                "insert_after": "one_fm_salary_details",
                "label": "Total Monthly Salary",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_salary_details",
                "fieldtype": "Table",
                "insert_after": "one_fm_salary_structure",
                "label": "Salary Details",
                "options": "ERF Salary Detail"
            },
            {
                "fieldname": "one_fm_salary_details_section",
                "fieldtype": "Section Break",
                "insert_after": "residency_fine_amount",
                "label": ""
            }
        ]
    }
