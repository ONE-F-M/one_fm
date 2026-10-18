def get_skill_assessment_properties():
    return [
        {
            "doc_type": "Skill Assessment",
            "doctype_or_field": "DocField",
            "field_name": "rating",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        },
        # Skill Assessment rows are normally seeded from the Interview Round's
        # Expected Skill Set. Since that table was hidden in favour of the Evaluation
        # Matrix Config, rounds can legitimately carry no expected skills, which left
        # interviewers with an empty grid they could not fill: `skill` is read only by
        # default, so "Add Row" produced a row that could never satisfy its own
        # mandatory check. Making it writable gives them a manual escape hatch.
        {
            "doc_type": "Skill Assessment",
            "doctype_or_field": "DocField",
            "field_name": "skill",
            "property": "read_only",
            "property_type": "Check",
            "value": "0"
        }
    ]
