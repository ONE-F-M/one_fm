from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.leave_application import get_leave_application_custom_fields


def execute():
	"""WI-001696: read-only Compensatory Leave Request link on Leave Application."""
	create_custom_fields(get_leave_application_custom_fields())
