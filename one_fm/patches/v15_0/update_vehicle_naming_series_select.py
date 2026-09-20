import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.vehicle import get_vehicle_custom_fields
from one_fm.custom.property_setter.vehicle import get_vehicle_properties
from one_fm.setup.setup import add_property_setter


def execute():
	"""
	Convert Vehicle custom_naming_series to a Select naming series field and
	set the Vehicle autoname Property Setter to field:custom_naming_series.
	"""
	# 1. Apply updated custom field (custom_naming_series -> Select)
	create_custom_fields(get_vehicle_custom_fields(), update=True)

	# 2. Apply the autoname Property Setter (field:custom_naming_series)
	add_property_setter(get_vehicle_properties())

	frappe.clear_cache(doctype="Vehicle")
