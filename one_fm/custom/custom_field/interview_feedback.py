def get_interview_feedback_custom_fields():
    return {
        "Interview Feedback": [
            {
                "fieldname": "custom_evaluation_criteria",
                "fieldtype": "Table",
                "label": "Evaluation Criteria",
                "options": "Interview Evaluation Detail",
                "insert_after": "feedback",
                "read_only": 1,
            },
            {
                "fieldname": "custom_remarks",
                "fieldtype": "Small Text",
                "label": "Remarks",
                "insert_after": "custom_evaluation_criteria",
            },
            {
                "fieldname": "interview_question_assessment_sb",
                "fieldtype": "Section Break",
                "insert_after": "skill_assessment",
            },
            {
                "fieldname": "interview_question_assessment",
                "fieldtype": "Table",
                "insert_after": "interview_question_assessment_sb",
                "label": "Interview Question Assessment",
                "options": "Interview Question Result",
            },
            {
                "fieldname": "career_history",
                "label": "Career History",
                "insert_after": "interview_round",
                "fieldtype": "Link",
                "options": "Career History",
                "read_only": 1,
            },
        ]
    }
