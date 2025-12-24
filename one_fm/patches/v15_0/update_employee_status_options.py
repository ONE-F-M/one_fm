from one_fm.custom.property_setter.employee import get_employee_properties
from one_fm.setup.setup import add_property_setter

def execute():
    add_property_setter(get_employee_properties())
