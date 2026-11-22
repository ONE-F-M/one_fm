import frappe

# The Record Update Property records configured on the BA site.
PROPERTIES = [
	{"property_name": "Department", "linked_doctype": "Department", "employee_field": "department"},
	{"property_name": "Designation", "linked_doctype": "Designation", "employee_field": "designation"},
	{"property_name": "Employment Type", "linked_doctype": "Employment Type", "employee_field": "employment_type"},
	{"property_name": "Reports To", "linked_doctype": "Employee", "employee_field": "reports_to"},
	{"property_name": "Shift Allocation", "linked_doctype": "Operations Shift", "employee_field": "shift"},
]


def execute():
	frappe.reload_doc("one_fm", "doctype", "record_update_property")
	for values in PROPERTIES:
		if not frappe.db.exists("Record Update Property", values["property_name"]):
			frappe.get_doc({"doctype": "Record Update Property", **values}).insert(ignore_permissions=True)
