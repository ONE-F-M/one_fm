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
            }
        ]
    }
    create_custom_fields(custom_fields)
