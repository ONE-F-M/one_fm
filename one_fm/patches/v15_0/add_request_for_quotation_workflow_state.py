from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.request_for_quotation import get_request_for_quotation_custom_fields


def execute():
	# The Request for Quotation Lifecycle map sets workflow_state.
	create_custom_fields(get_request_for_quotation_custom_fields())
