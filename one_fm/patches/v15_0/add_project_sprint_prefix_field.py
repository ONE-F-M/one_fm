"""Add the "Sprint Prefix" (custom_sprint_prefix) custom field to Project.

A Data field shown/required only for SCRUM projects (depends_on /
mandatory_depends_on eval:doc.type=="SCRUM"), inserted after the "type" field.

The definition lives in one_fm.custom.custom_field.project (the source of
truth); this patch re-applies the full Project custom-field set with
update=True, so it is idempotent and also reconciles any drift in the other
Project fields.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.project import get_project_custom_fields


def execute():
    create_custom_fields(get_project_custom_fields(), update=True)
