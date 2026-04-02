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
            }
        ]
    }
