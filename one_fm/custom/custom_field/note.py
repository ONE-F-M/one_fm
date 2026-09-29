def get_note_custom_fields():
	return {
		"Note": [
			{
				"fieldname": "custom_pr_test",
				"label": "pr_Test",
				"fieldtype": "Data",
				"insert_after": "seen_by",
				"translatable": 1,
			},
		],
	}
