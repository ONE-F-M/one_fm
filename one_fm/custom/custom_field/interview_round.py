def get_interview_round_custom_fields():
    return {
        "Interview Round": [
            {
                "fieldname": "one_fm_nationality",
                "fieldtype": "Link",
                "label": "Nationality",
                "options": "Nationality",
                "insert_after": "designation",
                "description": "Used by Interview Console to match applicant nationality to the correct round.",
                "reqd": 1,
                "module": "one_fm",
            },
            {
                "fieldname": "interview_questions_sb",
                "fieldtype": "Section Break",
                "insert_after": "expected_skill_set",
                "label": "Interview Questions",
                "module": "one_fm",
            },
            {
                "fieldname": "interview_question",
                "fieldtype": "Table",
                "insert_after": "interview_questions_sb",
                "options": "Interview Questions",
                "module": "one_fm",
            },
            {
                "fieldname": "interview_matrix_sb",
                "fieldtype": "Section Break",
                "label": "Evaluation Matrix Config",
                "insert_after": "interview_question",
                "module": "one_fm"
            },
            {
                "fieldname": "interview_matrix",
                "fieldtype": "Table",
                "label": "Interview Questions Setup",
                "options": "Interview Matrix Question",
                "insert_after": "interview_matrix_sb",
                "module": "one_fm"
            }
        ]
    }
