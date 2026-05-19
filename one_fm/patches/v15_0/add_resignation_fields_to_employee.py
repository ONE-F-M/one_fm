import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.employee import get_employee_custom_fields

def execute():
	all_fields = get_employee_custom_fields()
	resignation_fields = [f for f in all_fields.get("Employee", []) if f.get("fieldname") in ["resignation_status", "current_resignation", "current_withdrawal", "resignation_section", "resignation_date"]]
	create_custom_fields({"Employee": resignation_fields}, ignore_validate=True, update=True)
