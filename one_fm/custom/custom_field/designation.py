def get_designation_custom_fields():
    return {
        "Designation": [
            {
                "fieldname": "custom_job_offer_term_template",
                "fieldtype": "Link",
                "insert_after": "designation_in_arabic",
                "label": "Job Offer Term Template",
                "options": "Job Offer Term Template"
            },
            {
                "fieldname": "appraisal_template",
                "fieldtype": "Link",
                "insert_after": "description",
                "label": "Appraisal Template",
                "options": "Appraisal Template",
                "allow_in_quick_entry": 1
            },
            {
                "fieldname": "skills",
                "fieldtype": "Table",
                "insert_after": "required_skills_section",
                "label": "Skills",
                "options": "Designation Skill"
            },
            {
                "fieldname": "required_skills_section",
                "fieldtype": "Section Break",
                "insert_after": "description",
                "label": "Required Skills"
            },
            {
                "fieldname": "custom_requires_high_school_certificate",
                "fieldtype": "Check",
                "insert_after": "skills",
                "label": "Requires High School Certificate",
                "description": "If checked, every job applicant for this role will have to attach their high school certificate while completing the job application form using magic link."
            },
            {
                "fieldname": "create_user_permission",
                "fieldtype": "Check",
                "insert_after": "role_profile",
                "label": "Create User Permission"
            },
            {
                "fieldname": "role_profile",
                "fieldtype": "Link",
                "insert_after": "user_and_roles",
                "label": "Role Profile",
                "options": "Role Profile"
            },
            {
                "fieldname": "user_and_roles",
                "fieldtype": "Section Break",
                "insert_after": "description",
                "label": "User and Roles"
            },
            {
                "fieldname": "designation_in_arabic",
                "fieldtype": "Data",
                "insert_after": "designation_abbreviation",
                "label": "Designation in Arabic",
                "translatable": 1
            },
            {
                "fieldname": "one_fm_uniforms",
                "fieldtype": "Table",
                "insert_after": "one_fm_is_uniform_needed_for_this_job",
                "options": "Designation Profile Item"
            },
            {
                "fieldname": "one_fm_uniforms_section",
                "fieldtype": "Section Break",
                "insert_after": "skills",
                "label": "Uniforms",
                "collapsible": 1
            },
            {
                "fieldname": "one_fm_is_uniform_needed_for_this_job",
                "fieldtype": "Check",
                "insert_after": "one_fm_uniforms_section",
                "label": "Is Uniform Needed for This Job"
            },
            {
                "fieldname": "designation_abbreviation",
                "fieldtype": "Data",
                "insert_after": "designation_name",
                "label": "Designation Abbreviation",
                "translatable": 1
            }
        ]
    }
