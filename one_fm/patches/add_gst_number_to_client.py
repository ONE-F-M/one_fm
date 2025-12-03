# one_fm/patches/add_gst_number_to_client.py
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	"""Ensure Client has required custom field 'gst_number' (Data)."""
	dt = "Client"
	fieldname = "gst_number"

	# Ensure target DocType exists
	if not frappe.db.exists("DocType", dt):
		return

	# If Custom Field already exists, ensure required
	cf_name = frappe.db.get_value(
		"Custom Field", {"dt": dt, "fieldname": fieldname}, "name"
	)
	if cf_name:
		cf = frappe.get_doc("Custom Field", cf_name)
		updated = False
		if cf.fieldtype != "Data":
			cf.fieldtype = "Data"
			updated = True
		if not cf.reqd:
			cf.reqd = 1
			updated = True
		if updated:
			cf.save(ignore_permissions=True)
		return

	# If field exists on DocType as a standard field, set it required via Property Setter
	meta = frappe.get_meta(dt)
	if meta.has_field(fieldname):
		# Ensure 'reqd' property is set to 1
		make_property_setter(dt, fieldname, "reqd", 1, "Check")
		return

	# Otherwise, create a new required Custom Field (Data)
	df = {
		"fieldname": fieldname,
		"label": "GST Number",
		"fieldtype": "Data",
		"reqd": 1,
		# Optionally set length to 15 if your GST format requires it; Frappe Data doesn't enforce length strictly
		# "length": 15,
	}
	create_custom_field(dt, df, ignore_validate=True)
