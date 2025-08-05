def get_timesheet_properties():
    return [
        {
            "doc_type": "Timesheet",
            "doctype_or_field": "DocType",
            "property": "links_order",
            "property_type": "Small Text",
            "value": '["38e508964c"]'
        },
        {
            "doc_type": "Timesheet",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "default",
            "property_type": "Text",
            "value": "TS-.YYYY.-"
        },
        {
            "doc_type": "Timesheet",
            "doctype_or_field": "DocType",
            "property": "autoname",
            "property_type": "Data",
            "value": "format:TMS-{YYYY}-{MM}-{DD}-{###}"
        },
        {
            "doc_type": "Timesheet",
            "doctype_or_field": "DocType",
            "property": "naming_rule",
            "property_type": "Data",
            "value": "Expression"
        },
        {
            "doc_type": "Timesheet",
            "doctype_or_field": "DocField",
            "field_name": "parent_project",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "employee.project"
        },
        {
            "doc_type": "Timesheet",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "options",
            "property_type": "Text",
            "value": "TS-.YYYY.-"
        }
    ]