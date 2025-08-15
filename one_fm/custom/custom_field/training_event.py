def get_training_event_custom_fields():
    return {
        "Training Event": [
            {
                "fieldname": "validity",
                "fieldtype": "Int",
                "label": "Validity",
                "insert_after": "has_certificate",
                "depends_on": "eval:doc.has_certificate==1",
                "description": "In Months"
            },
            {
                "fieldname": "minimum_score",
                "fieldtype": "Float",
                "label": "Minimum Score",
                "insert_after": "validity",
                "depends_on": "eval:doc.has_certificate==1",
                "precision": "1"
            }
        ]
    }