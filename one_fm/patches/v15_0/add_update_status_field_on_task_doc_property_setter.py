import frappe
from one_fm.setup import add_property_setter
from one_fm.custom.property_setter.update_status_field_on_task import get_status_field_task_properties

def execute():
    add_property_setter(get_status_field_task_properties())
