import frappe
from one_fm.setup import add_property_setter
from one_fm.custom.property_setter.task import get_task_properties

def execute():
    add_property_setter(get_task_properties())
