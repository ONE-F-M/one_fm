def get_country_custom_fields():
    return {
        "Country": [
            {
                "fieldname": "one_fm_tel_code",
                "fieldtype": "Data",
                "insert_after": "code_alpha3",
                "label": "Country Code",
                "hidden": 0,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_country_name_arabic",
                "fieldtype": "Data",
                "insert_after": "country_name",
                "label": "Country Name (ARABIC)",
                "hidden": 0,
                "translatable": 1
            },
            {
                "fieldname": "code_alpha3",
                "fieldtype": "Data",
                "insert_after": "code",
                "label": "Code Alpha3",
                "description": "Alpha 3 code",
                "hidden": 0,
                "translatable": 1
            }
        ]
    }
