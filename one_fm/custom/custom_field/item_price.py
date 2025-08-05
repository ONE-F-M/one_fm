def get_item_price_custom_fields():
    return {
        "Item Price": [
            {
                "label": "Post Detail",
                "fieldname": "post_detail",
                "insert_after": "item_description",
                "fieldtype": "Section Break"
            },
            {
                "fieldname": "gender",
                "fieldtype": "Link",
                "insert_after": "post_detail",
                "label": "Gender",
                "options": "Gender"
            },
            {
                "fieldname": "shift_hours",
                "fieldtype": "Float",
                "insert_after": "gender",
                "label": "Shift Hours"
            },
            {
                "fieldname": "column_break_10",
                "fieldtype": "Column Break",
                "insert_after": "shift_hours"
            },
            {
                "fieldname": "days_off",
                "fieldtype": "Select",
                "insert_after": "column_break_10",
                "label": "Days Off",
                "options": "0\n1\n2\n3\n4\n5\n6"
            }
        ]
    }
