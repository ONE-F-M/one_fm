def get_gender_custom_fields():
    return {
        "Gender": [
            {
                "fieldname": "gender_arabic",
                "fieldtype": "Data",
                "insert_after": "gender",
                "label": "Gender (ARABIC)",
                "translatable": 1
            },
            {
                "fieldname": "custom_maternity_required",
                "fieldtype": "Check",
                "insert_after": "gender_arabic",
                "label": "Eligible for Maternity Leave"
            }
        ]
    }
