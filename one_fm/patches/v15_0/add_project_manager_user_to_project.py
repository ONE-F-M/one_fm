"""Add Project Manager User (custom_project_manager_user) to Project, fetched from the project manager's user id."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.project import get_project_custom_fields


def execute():
	create_custom_fields(get_project_custom_fields(), update=True)
