import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add courier tracking custom fields to Supplier, Purchase Order, Purchase Receipt, and Purchase Invoice."""
	from one_fm.custom.custom_field.supplier import get_supplier_custom_fields
	from one_fm.custom.custom_field.purchase_order import get_purchase_order_custom_fields
	from one_fm.custom.custom_field.purchase_receipt import get_purchase_receipt_custom_fields
	from one_fm.custom.custom_field.purchase_invoice import get_purchase_invoice_custom_fields

	custom_fields = {}
	custom_fields.update(get_supplier_custom_fields())
	custom_fields.update(get_purchase_order_custom_fields())
	custom_fields.update(get_purchase_receipt_custom_fields())
	custom_fields.update(get_purchase_invoice_custom_fields())

	create_custom_fields(custom_fields, update=True)
