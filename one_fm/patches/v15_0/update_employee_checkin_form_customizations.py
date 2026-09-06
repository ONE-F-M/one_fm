from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.employee_checkin import get_employee_checkin_custom_fields
from one_fm.custom.property_setter.employee_checkin import get_employee_checkin_properties
from one_fm.setup.setup import add_property_setter


def execute():
    add_property_setter(get_employee_checkin_properties())
    create_custom_fields(get_employee_checkin_custom_fields())
