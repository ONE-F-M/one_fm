import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.sales_invoice_item import get_sales_invoice_item_custom_fields

NEW_FIELDS = (
	"custom_margin_type",
	"custom_margin_rate_or_amount",
	"custom_base_amount",
	"custom_margin_display",
)


def execute():
	"""WI-004512: add the selling-margin fields to Sales Invoice Item.

	Only the four new fields are passed, not the whole Sales Invoice Item set, so other
	customised fields on the site are not touched.
	"""
	all_fields = get_sales_invoice_item_custom_fields()
	fields = {
		"Sales Invoice Item": [
			field for field in all_fields["Sales Invoice Item"] if field["fieldname"] in NEW_FIELDS
		]
	}
	create_custom_fields(fields, update=True)

	# create_custom_fields only syncs the table when it inserted or changed a field.
	frappe.db.updatedb("Sales Invoice Item")
