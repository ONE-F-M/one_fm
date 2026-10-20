from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.asset_repair import get_asset_repair_custom_fields

def execute():
	create_custom_fields(get_asset_repair_custom_fields())
