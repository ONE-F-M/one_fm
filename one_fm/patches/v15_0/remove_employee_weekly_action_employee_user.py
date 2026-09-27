from one_fm.setup.setup import delete_custom_fields


def execute():
	# Added by hand on a site rather than in code; the doctype never read it.
	delete_custom_fields({"Employee Weekly Action": [{"fieldname": "employee_user"}]})
