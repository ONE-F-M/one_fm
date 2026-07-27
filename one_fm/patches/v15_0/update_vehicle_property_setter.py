from one_fm.setup.setup import add_property_setter
import frappe

def execute():
    frappe.db.delete("Property Setter", {
		"doc_type": "Vehicle",
		"field_name": "employee",
	})
    property_setters = [
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "mandatory_depends_on",
            "value": "eval:doc.one_fm_vehicle_category != 'Subcontractor'"
        }
    ]
    add_property_setter(property_setters)