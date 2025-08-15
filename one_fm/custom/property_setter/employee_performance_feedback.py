def get_employee_performance_feedback_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Performance Feedback",
            "doctype_or_field": "DocField",
            "field_name": "appraisal",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Performance Feedback",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        }
    ]
