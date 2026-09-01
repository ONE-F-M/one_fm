from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.property_setter.employee_checkin import get_employee_checkin_properties
from one_fm.setup.setup import add_property_setter


def execute():
    add_property_setter(get_employee_checkin_properties())

    custom_fields = {
        "Employee Checkin": [
            {
                "fieldname": "source",
                "fieldtype": "Select",
                "insert_after": "employee_checkin_issue",
                "label": "Source",
                "options": "\nMobile App\nMobile Web\nCheck-in Form\nFrappe Page\nAttendance Check",
                "default": "",
                "translatable": 1
            },
            {
                "fieldname": "shift_assignment",
                "fieldtype": "Link",
                "insert_after": "shift_details",
                "label": "Shift Assignment",
                "options": "Shift Assignment",
                "read_only": 1
            },
            {
                "fieldname": "roster_type",
                "fieldtype": "Data",
                "insert_after": "post_abbrv",
                "label": "Roster Type",
                "fetch_from": "shift_assignment.roster_type",
                "fetch_if_empty": 1,
                "translatable": 1,
                "read_only": 1
            }
        ]
    }
    create_custom_fields(custom_fields)
