from one_fm.setup.setup import add_property_setter
from one_fm.custom.property_setter.todo import get_todo_properties


def execute():
	"""Make the ToDo type field read-only."""
	add_property_setter(get_todo_properties())
