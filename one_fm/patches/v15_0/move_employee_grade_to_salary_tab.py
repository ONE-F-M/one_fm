"""WI-002605 / WI-002606: Grade belongs on the Salary tab, not Government Relation.

Layout only - the field itself is untouched, so nothing that reads or writes Grade changes.
It is a standard HRMS field whose stock home IS the salary section; this app's field_order
had moved it under Government Relation, and this puts it back.

add_property_setter rewrites the whole Employee field_order, which is the only way to move
one field: the order is a single stored list, not a per-field property.
"""

from one_fm.custom.property_setter.employee import get_employee_properties
from one_fm.setup.setup import add_property_setter


def execute():
	add_property_setter(get_employee_properties())
