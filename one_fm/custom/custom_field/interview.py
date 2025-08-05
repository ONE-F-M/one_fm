def get_interview_custom_fields():
    return {
        "Interview": [
            {
                "fieldname": "custom_hiring_method",
                "fieldtype": "Data",
                "insert_after": "job_applicant",
                "label": "Hiring Method",
                "fetch_from": "job_applicant.one_fm_hiring_method",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "career_history",
                "fieldtype": "Link",
                "insert_after": "custom_hiring_method",
                "label": "Career History",
                "options": "Career History",
                "read_only": 1
            },
            {
                "fieldname": "interview_round_child_ref",
                "fieldtype": "Link",
                "insert_after": "career_history",
                "label": "Interview Round Child Ref",
                "options": "Job Applicant Interview Round",
                "hidden": 1
            }
        ]
    }
