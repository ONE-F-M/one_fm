def get_process_creation_request_properties():
	return [
		{
			"doctype_or_field": "DocField",
			"doc_type": "Process Creation Request",
			"field_name": "naming_series",
			"property": "options",
			"property_type": "Text",
			"value": "PBR-PCR-.YYYY.-.MM.-.####",
		},
		{
			"doctype_or_field": "DocField",
			"doc_type": "Process Creation Request",
			"field_name": "parent_process",
			"property": "link_filters",
			"property_type": "JSON",
			"value": "[[\"Process\",\"is_group\",\"=\",1]]",
		},
	]
