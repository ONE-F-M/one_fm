def get_interview_feedback_custom_fields():
    return {
        "Interview Feedback": [
            {
                "fieldname": "interview_question_assessment_sb",
                "fieldtype": "Section Break",
                "insert_after": "skill_assessment"
            },
            {
                "fieldname": "interview_question_assessment",
                "fieldtype": "Table",
                "insert_after": "interview_question_assessment_sb",
                "label": "Interview Question Assessment",
                "options": "Interview Question Result"
            },
            {
                "fieldname": "section_break_11",
                "fieldtype": "Section Break",
                "insert_after": "interview_question_assessment"
            },
            {
                "label": "Career History",
                "fieldname": "career_history",
                "insert_after": "interview_round",
                "fieldtype": "Link",
                "options": "Career History",
                "read_only": 1
            }
        ]
    }
