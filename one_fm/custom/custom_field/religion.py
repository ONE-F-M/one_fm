def get_religion_custom_fields():
    return {
        "Religion": [
            {
                "fieldname": "custom_hajj_check_required",
                "label": "Eligible for Hajj",
                "fieldtype": "Check",
                "insert_after": "religion_arabic"
            }
        ]
    }
