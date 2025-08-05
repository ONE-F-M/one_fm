def get_interview_round_custom_fields():
    return {
        "Interview Round": [
            {
                "fieldname": "interview_questions_sb",
                "fieldtype": "Section Break",
                "insert_after": "expected_skill_set",
                "label": "Interview Questions"
            },
            {
                "fieldname": "interview_question",
                "fieldtype": "Table",
                "insert_after": "interview_questions_sb",
                "options": "Interview Questions"
            }
        ]
    }
