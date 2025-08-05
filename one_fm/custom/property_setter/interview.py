def get_interview_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "from_time",
            "property": "default",
            "property_type": "Text",
            "value": ""
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "from_time",
            "property": "mandatory_depends_on",
            "property_type": "Data",
            "value": "eval: doc.custom_hiring_method !=\"A la carte Recruitment\""
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "from_time",
            "property": "reqd",
            "property_type": "Check",
            "value": 0
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "from_time",
            "property": "set_only_once",
            "property_type": "0",
            "value": None
        },
        {
            "doctype_or_field": "DocType",
            "doc_type": "Interview",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"interview_details_section\", \"interview_round\", \"job_applicant\", \"custom_hiring_method\", \"career_history\", \"interview_round_child_ref\", \"job_opening\", \"designation\", \"resume_link\", \"column_break_4\", \"status\", \"scheduled_on\", \"from_time\", \"to_time\", \"section_break_hqvh\", \"interview_details\", \"ratings_section\", \"expected_average_rating\", \"column_break_12\", \"average_rating\", \"section_break_13\", \"interview_summary\", \"reminded\", \"amended_from\", \"feedback_tab\", \"feedback_html\"]"
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "to_time",
            "property": "default",
            "property_type": "Text",
            "value": ""
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "to_time",
            "property": "mandatory_depends_on",
            "property_type": "Data",
            "value": "eval: doc.custom_hiring_method !=\"A la carte Recruitment\""
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "to_time",
            "property": "reqd",
            "property_type": "Check",
            "value": 0
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Interview",
            "field_name": "to_time",
            "property": "set_only_once",
            "property_type": "0",
            "value": None
        }
    ]
