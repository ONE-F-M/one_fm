from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.asset import get_asset_custom_fields


def execute():
	create_custom_fields(get_asset_custom_fields(), update=True)
