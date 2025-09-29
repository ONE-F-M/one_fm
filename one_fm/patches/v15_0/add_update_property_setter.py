import frappe

from one_fm.setup.property_setter import get_field_properties
from one_fm.setup.setup import add_property_setter

def execute():
    add_property_setter(get_field_properties())
