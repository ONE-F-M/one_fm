from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.purchase_receipt import get_purchase_receipt_custom_fields


def execute():
	# The Purchase Receipt Lifecycle map sets workflow_state.
	create_custom_fields(get_purchase_receipt_custom_fields())
