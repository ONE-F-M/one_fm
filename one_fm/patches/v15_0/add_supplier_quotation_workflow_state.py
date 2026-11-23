from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.supplier_quotation import get_supplier_quotation_custom_fields


def execute():
	# The Supplier Quotation Lifecycle map sets workflow_state.
	create_custom_fields(get_supplier_quotation_custom_fields())
