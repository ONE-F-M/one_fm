def get_job_opening_custom_fields():
    return {
        "Job Opening": [
            {
                "fieldname": "one_fm_designation_skill",
                "fieldtype": "Table",
                "label": "Designation Skill",
                "options": "Designation Skill",
                "insert_after": "one_fm_basic_skill_section",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_basic_skill_section",
                "fieldtype": "Section Break",
                "label": "Basic Skills",
                "collapsible": 1,
                "insert_after": "one_fm_languages"
            },
            {
                "fieldname": "one_fm_active_willing_agency_section",
                "fieldtype": "Section Break",
                "label": "Agencies",
                "collapsible": 1,
                "insert_after": "one_fm_sourcing_team"
            },
            {
                "fieldname": "one_fm_active_willing_agency",
                "fieldtype": "Table",
                "options": "Active Willing Agency",
                "insert_after": "one_fm_active_willing_agency_section"
            },
            {
                "fieldname": "job_title_in_arabic",
                "fieldtype": "Data",
                "label": "Job Title in Arabic",
                "insert_after": "column_break_5",
                "reqd": 1,
                "translatable": 1
            },
            {
                "fieldname": "is_head_hunting_required",
                "fieldtype": "Check",
                "label": "Is Head Hunting Required",
                "insert_after": "one_fm_source_of_hire"
            },
            {
                "fieldname": "allow_easy_apply",
                "fieldtype": "Check",
                "label": "Allow Easy Apply",
                "depends_on": "publish",
                "hidden": 1,
                "insert_after": "publish"
            },
            {
                "fieldname": "one_fm_sourcing_team",
                "fieldtype": "Select",
                "label": "Sourcing Team",
                "options": "\nOne FM\nAgency\nOne FM and Agency",
                "insert_after": "one_fm_hire_details_cb",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_source_of_hire",
                "fieldtype": "Select",
                "label": "Source of Hire",
                "options": "\nLocal\nOverseas\nLocal and Overseas",
                "insert_after": "one_fm_hire_details_section",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_performance_profile",
                "fieldtype": "Data",
                "label": "Performance Profile",
                "insert_after": "one_fm_designation_skill",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_no_of_positions_by_erf",
                "fieldtype": "Int",
                "label": "Number of Positions",
                "insert_after": "planned_vacancies",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_minimum_experience_required",
                "fieldtype": "Float",
                "label": "Minimum Experience Required",
                "insert_after": "one_fm_hiring_manager",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_minimum_age_required",
                "fieldtype": "Float",
                "label": "Minimum Age Required",
                "insert_after": "one_fm_maximum_experience_required",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_maximum_experience_required",
                "fieldtype": "Float",
                "label": "Maximum Experience Required",
                "insert_after": "one_fm_minimum_experience_required",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_maximum_age_required",
                "fieldtype": "Float",
                "label": "Maximum Age Required",
                "insert_after": "one_fm_minimum_age_required",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_languages",
                "fieldtype": "Table",
                "options": "Employee Language Requirement",
                "insert_after": "one_fm_language_section",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_language_section",
                "fieldtype": "Section Break",
                "label": "Language",
                "collapsible": 1,
                "insert_after": "one_fm_job_post_valid_till",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_job_post_valid_till",
                "fieldtype": "Date",
                "label": "Job Post Valid Till",
                "insert_after": "one_fm_job_opening_created"
            },
            {
                "fieldname": "one_fm_job_opening_created",
                "fieldtype": "Date",
                "label": "Job Opening Created",
                "insert_after": "one_fm_no_of_positions_by_erf",
                "default": "Today",
                "read_only": 1
            },
            {
                "fieldname": "one_fm_hiring_manager",
                "fieldtype": "Link",
                "label": "Hiring Manager",
                "options": "Employee",
                "insert_after": "status",
                "ignore_user_permissions": 1,
                "read_only": 1
            },
            {
                "fieldname": "one_fm_hire_details_section",
                "fieldtype": "Section Break",
                "insert_after": "description"
            },
            {
                "fieldname": "one_fm_hire_details_cb",
                "fieldtype": "Column Break",
                "insert_after": "is_head_hunting_required"
            },
            {
                "fieldname": "one_fm_erf",
                "fieldtype": "Link",
                "label": "ERF",
                "options": "ERF",
                "insert_after": "column_break_5",
                "reqd": 1
            },
            {
                "label": "Description in Arabic",
                "fieldname": "description_in_arabic",
                "insert_after": "description",
                "fieldtype": "Text Editor"
            }
        ]
    }
