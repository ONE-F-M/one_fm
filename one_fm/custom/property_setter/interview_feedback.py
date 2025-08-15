def get_interview_feedback_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview Feedback",
            "field_name": "result",
            "property": "default",
            "property_type": "Text",
            "value": "Pending"
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview Feedback",
            "field_name": "result",
            "property": "options",
            "property_type": "Text",
            "value": "\nCleared\nRejected\nPending"
        }
    ]
