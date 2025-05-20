import frappe
from frappe.custom.doctype.property_setter.property_setter import delete_property_setter as core_delete_property_setter

def create_property_setter(property_setters:dict):
    """
    Create or update Property Setters.

    Args:
        property_setters (dict): A dictionary where keys are DocTypes and values are lists of property setter dicts.
            Example:
                {
                    'Sales Invoice': [
                        {
                            'doctype': 'Property Setter',
                            'doctype_or_field': 'DocField',
                            'doc_type': 'Sales Invoice',
                            'property': 'read_only',
                            'property_type': 'Check',
                            'value': '1',
                            'name': 'Sales Invoice-read_only',
                            'is_system_generated': 1
                        }
                    ]
                }

    Returns:
        None
    """
    doctypes_to_update = set()
    for doctypes, field_properties in property_setters.items():
        if isinstance(field_properties, dict):
            # only one field
            field_properties = [field_properties]

        if isinstance(doctypes, str):
            # only one doctype
            doctypes = (doctypes,)

        for doctype in doctypes:
            doctypes_to_update.add(doctype)

            for field_property in field_properties:
                property_setter = frappe.db.get_value(
                    "Property Setter",
                    {"doc_type": doctype, "property": field_property["property"]}
                )
                if not property_setter:
                    try:
                        field_property = field_property.copy()
                        field_property["owner"] = "Administrator"
                        frappe.get_doc(field_property).insert(ignore_permissions=True)
                    except frappe.exceptions.DuplicateEntryError:
                        pass

                else:
                    property_setter_obj = frappe.get_doc("Property Setter", property_setter)
                    property_setter_obj.update(field_property)
                    property_setter_obj.save()

    for doctype in doctypes_to_update:
        frappe.clear_cache(doctype=doctype)
        frappe.db.updatedb(doctype)

def delete_property_setter(property_setters: dict):
    """
    Delete property setters based on doc_type and property.
    Args:
        property_setters (dict): A dictionary where keys are DocTypes and values are lists of property dicts.
            Example:
                {
                    'Sales Invoice': [
                        {'property': 'read_only', 'field_name': 'posting_date'},
                        {'property': 'field_order'}
                    ]
                }

    Returns:
        None
    """
    for doctype, field_properties in property_setters.items():
        for prop in field_properties:
            property_name = prop.get("property")
            field_name = prop.get("field_name")
            row_name = prop.get("row_name")

            if property_name:
                core_delete_property_setter(
                    doc_type=doctype,
                    property=property_name,
                    field_name=field_name,
                    row_name=row_name
                )

        frappe.clear_cache(doctype=doctype)
