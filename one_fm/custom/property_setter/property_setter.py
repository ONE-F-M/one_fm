import frappe

def create_property_setter(property_setters:dict):
    '''
        Method used to create/update property setter.
        Args:
            :param property_setters: example `{'Sales Invoice': [dict(property='read_only')]}`"""
            property_setters (dict): List of dictionary representing the property setter data.
                - is_system_generated(int): To state this property is system generated
                - doctype_or_field(str): Whether the property setter for DocType or Filed
                - doc_type(str): The internal document type associated with the Property Setter
                - property(str): Which property we need to update(eg: field_order)
                - property_type(str): Set the property type
                - value(str): Value of the property
                - doctype(str): The DocType Property Setter
                - name(str): Name of the Property Setter record
        Returns:
            None
    '''
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
                property_setter = frappe.db.get_value("Property Setter", {"doc_type": doctype, "property": field_property["property"]})
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
	:param property_setters: a dict like `{'Property Setter': [{property: 'field_order', ...}]}`
	"""
	for doctype, field_properties in property_setters.items():
		frappe.db.delete(
			"Property Setter",
			{
				"property": ("in", [field_property["property"] for field_property in field_properties]),
				"doc_type": doctype,
			},
		)

		frappe.clear_cache(doctype=doctype)
