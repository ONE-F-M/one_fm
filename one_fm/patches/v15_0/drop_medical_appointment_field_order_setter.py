import frappe


def execute():
	# A Customize Form field_order setter pins the old layout and leaves Payment References empty.
	frappe.db.delete("Property Setter", {"doc_type": "Medical Appointment", "property": "field_order"})
	frappe.clear_cache(doctype="Medical Appointment")
