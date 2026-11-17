import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

# WI-004748: the HR Settings field that says who is emailed three days after an Employee is
# created. create_custom_fields updates a field that already exists instead of duplicating
# it, so re-running is idempotent.


def execute():
	create_custom_fields(get_hr_settings_custom_fields())
	frappe.clear_cache(doctype="HR Settings")
